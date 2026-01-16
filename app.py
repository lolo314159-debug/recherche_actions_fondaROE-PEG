import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import datetime
import requests
import time

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Screener Actions S&P500 & CAC40", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. FONCTIONS DE LECTURE ET SAUVEGARDE ---
def get_data(sheet_name):
    """Lit les données depuis Google Sheets avec gestion d'erreurs."""
    try:
        return conn.read(worksheet=sheet_name, ttl=0)
    except Exception:
        if sheet_name == "index_composition":
            return pd.DataFrame(columns=['indice', 'ticker', 'nom', 'date_recup'])
        return pd.DataFrame(columns=['ticker', 'roe', 'peg', 'prix', 'date_recup'])

def save_data(df, sheet_name):
    """Enregistre les données en évitant les doublons de tickers."""
    try:
        existing = get_data(sheet_name)
        # Fusionner et garder la version la plus récente du ticker
        updated = pd.concat([existing, df], ignore_index=True)
        updated = updated.drop_duplicates(subset=['ticker'], keep='last')
        # Nettoyage de sécurité avant envoi
        if 'ticker' in updated.columns:
            updated = updated[updated['ticker'].str.contains(r'[A-Za-z]', na=False)]
        
        conn.update(worksheet=sheet_name, data=updated)
        return True
    except Exception as e:
        st.error(f"Erreur de sauvegarde : {e}")
        return False

# --- 3. VARIABLES GLOBALES ---
today = datetime.now().strftime('%Y-%m-%d')
df_comp = get_data("index_composition")

# --- 4. INTERFACE UTILISATEUR ---
st.title("🛡️ Screener Intelligent & Archive Cloud")

# --- SECTION 1 : RÉPERTOIRE DES INDICES ---
with st.expander("📁 Étape 1 : Gérer le répertoire des indices (Wikipedia)"):
    st.write("Cette section met à jour la liste des actions disponibles sans les erreurs de colonnes.")
    
    if st.button("🔄 Synchroniser les Tickers (Nettoyage complet)"):
        with st.spinner("Alignement des données Wikipedia..."):
            header = {"User-Agent": "Mozilla/5.0"}
            
            # --- CAC 40 ---
            # Colonne 0 = Company (Nom), Colonne 3 = Ticker
            r_cac = requests.get("https://en.wikipedia.org/wiki/CAC_40", headers=header)
            df_cac_raw = pd.read_html(r_cac.text)[0]
            df_cac = pd.DataFrame({
                'ticker': df_cac_raw.iloc[:, 3].astype(str),
                'nom': df_cac_raw.iloc[:, 0].astype(str),
                'indice': 'CAC 40'
            })

            # --- S&P 500 ---
            # Colonne 0 = Symbol (Ticker), Colonne 1 = Security (Nom)
            r_sp = requests.get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", headers=header)
            df_sp_raw = pd.read_html(r_sp.text)[0]
            df_sp = pd.DataFrame({
                'ticker': df_sp_raw.iloc[:, 0].astype(str).str.replace('.', '-', regex=True),
                'nom': df_sp_raw.iloc[:, 1].astype(str),
                'indice': 'S&P 500'
            })

            # --- FUSION ET FILTRE ANTI-TIRETS ---
            full_comp = pd.concat([df_cac, df_sp])
            # On ne garde que les tickers valides (contenant des lettres) pour éviter les "---"
            full_comp = full_comp[full_comp['ticker'].str.contains(r'[A-Za-z]', na=False)]
            full_comp['date_recup'] = today
            
            # Écrasement propre du répertoire
            conn.update(worksheet="index_composition", data=full_comp)
            st.success("Répertoire mis à jour avec succès !")
            st.rerun()

    if not df_comp.empty:
        st.dataframe(df_comp, use_container_width=True, hide_index=True)

# --- SECTION 2 : COLLECTE DES DONNÉES FINANCIÈRES ---
st.divider()
st.subheader("🔍 Étape 2 : Analyse financière")

if not df_comp.empty:
    col_idx, col_stock = st.columns(2)
    
    with col_idx:
        indice_choisi = st.selectbox("Sélectionner l'indice", df_comp['indice'].unique())
    
    # Filtrer le répertoire pour l'indice choisi
    stocks_dispo = df_comp[df_comp['indice'] == indice_choisi].sort_values('nom')
    
    with col_stock:
        nom_choisi = st.selectbox("Choisir l'entreprise", stocks_dispo['nom'].tolist())
    
    # Récupérer le ticker exact correspondant au nom
    ticker_final = stocks_dispo[stocks_dispo['nom'] == nom_choisi]['ticker'].values[0]

    if st.button(f"🚀 Analyser {nom_choisi} ({ticker_final})"):
        with st.spinner(f"Récupération de {ticker_final} sur Yahoo..."):
            try:
                stock_obj = yf.Ticker(ticker_final)
                info = stock_obj.info
                
                # Création de la ligne de données
                nouvelle_ligne = pd.DataFrame([{
                    "ticker": ticker_final,
                    "roe": round(info.get("returnOnEquity", 0) * 100, 2),
                    "peg": info.get("trailingPegRatio", info.get("pegRatio", 0)),
                    "prix": info.get("currentPrice", 0),
                    "date_recup": today
                }])
                
                if save_data(nouvelle_ligne, "stock_data"):
                    st.success(f"Données de {nom_choisi} enregistrées au {today}")
            except Exception as e:
                st.error(f"Erreur Yahoo Finance pour {ticker_final} : {e}")

# --- SECTION 3 : AFFICHAGE DES RÉSULTATS ARCHIVÉS ---
st.divider()
df_final = get_data("stock_data")

if not df_final.empty:
    st.subheader("📊 Base de données financières collectées")
    
    # Filtres rapides
    c1, c2 = st.columns(2)
    min_roe = c1.slider("Filtrer par ROE min (%)", -50, 100, 10)
    
    # Conversion numérique pour le filtrage
    df_final['roe'] = pd.to_numeric(df_final['roe'], errors='coerce')
    df_final_filtered = df_final[df_final['roe'] >= min_roe]
    
    st.dataframe(
        df_final_filtered.sort_values("date_recup", ascending=False), 
        use_container_width=True, 
        hide_index=True
    )
else:
    st.info("Aucune donnée financière en base. Utilisez l'Étape 2 pour analyser une action.")
