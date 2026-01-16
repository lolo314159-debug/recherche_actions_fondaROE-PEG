import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import datetime
import requests

# --- CONFIGURATION ---
st.set_page_config(page_title="Screener Définitif", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FONCTIONS DE BASE ---
def get_data(sheet_name):
    try:
        return conn.read(worksheet=sheet_name, ttl=0)
    except:
        return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        existing = get_data(sheet_name)
        updated = pd.concat([existing, df], ignore_index=True).drop_duplicates(subset=['ticker'], keep='last')
        conn.update(worksheet=sheet_name, data=updated)
        return True
    except:
        return False

# --- VARIABLES ---
today = datetime.now().strftime('%Y-%m-%d')
df_comp = get_data("index_composition")

st.title("🛡️ Screener Stable & Répertoire")

# --- ETAPE 1 : RÉPERTOIRE (index_composition) ---
with st.expander("📁 Gérer le répertoire (index_composition)"):
# --- REMPLACEZ LE BLOC DE MISE À JOUR PAR CELUI-CI ---

if st.button("🧹 Réparer et Synchroniser le Répertoire"):
    with st.spinner("Alignement des colonnes Wikipedia..."):
        header = {"User-Agent": "Mozilla/5.0"}
        
        # --- TRAITEMENT CAC 40 ---
        r_cac = requests.get("https://en.wikipedia.org/wiki/CAC_40", headers=header)
        df_cac_raw = pd.read_html(r_cac.text)[0]
        # Colonne 0 = Company (Nom), Colonne 3 = Ticker
        df_cac = pd.DataFrame({
            'ticker': df_cac_raw.iloc[:, 3].astype(str),
            'nom': df_cac_raw.iloc[:, 0].astype(str),
            'indice': 'CAC 40'
        })

        # --- TRAITEMENT S&P 500 ---
        r_sp = requests.get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", headers=header)
        df_sp_raw = pd.read_html(r_sp.text)[0]
        # Colonne 0 = Symbol (Ticker), Colonne 1 = Security (Nom)
        df_sp = pd.DataFrame({
            'ticker': df_sp_raw.iloc[:, 0].astype(str).str.replace('.', '-', regex=True),
            'nom': df_sp_raw.iloc[:, 1].astype(str),
            'indice': 'S&P 500'
        })

        # --- NETTOYAGE DES TIRETS ET DOUBLONS ---
        full_comp = pd.concat([df_cac, df_sp])
        # Filtre de sécurité : le ticker doit contenir au moins une lettre
        full_comp = full_comp[full_comp['ticker'].str.contains(r'[A-Za-z]', na=False)]
        full_comp['date_recup'] = today
        
        # Mise à jour de la feuille
        conn.update(worksheet="index_composition", data=full_comp)
        st.success("Répertoire synchronisé : Noms et Tickers sont maintenant alignés !")
        st.rerun()
    
    st.dataframe(df_comp, use_container_width=True, hide_index=True)

# --- ETAPE 2 : ANALYSE (stock_data) ---
st.divider()
if not df_comp.empty:
    st.subheader("🔍 Analyse et mise à jour des données")
    
    # On sélectionne dans le répertoire
    col1, col2 = st.columns(2)
    with col1:
        target_idx = st.selectbox("Indice", df_comp['indice'].unique())
    with col2:
        list_stocks = df_comp[df_comp['indice'] == target_idx]['nom'].sort_values().tolist()
        target_name = st.selectbox("Action", list_stocks)
    
    ticker = df_comp[df_comp['nom'] == target_name]['ticker'].values[0]
    
    if st.button(f"🚀 Analyser/Actualiser {target_name} ({ticker})"):
        with st.spinner(f"Analyse de {ticker}..."):
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                new_data = pd.DataFrame([{
                    "ticker": ticker,
                    "roe": round(info.get("returnOnEquity", 0) * 100, 2),
                    "peg": info.get("trailingPegRatio", info.get("pegRatio", 0)),
                    "prix": info.get("currentPrice", 0),
                    "date_recup": today
                }])
                if save_data(new_data, "stock_data"):
                    st.success(f"Données de {ticker} enregistrées au {today}")
            except Exception as e:
                st.error(f"Erreur Yahoo : {e}")

# --- ETAPE 3 : AFFICHAGE FINAL ---
st.divider()
df_res = get_data("stock_data")
if not df_res.empty:
    st.subheader("📊 Résultats archivés")
    st.dataframe(df_res.sort_values("date_recup", ascending=False), use_container_width=True, hide_index=True)
