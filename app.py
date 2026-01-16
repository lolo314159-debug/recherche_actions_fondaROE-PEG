import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import datetime
import requests

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Screener Stable Pro", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. FONCTIONS DE LECTURE / ÉCRITURE ---
def get_data(sheet_name):
    try:
        return conn.read(worksheet=sheet_name, ttl=0)
    except:
        # Retourne un DataFrame vide avec les bonnes colonnes si la feuille n'existe pas
        if sheet_name == "index_composition":
            return pd.DataFrame(columns=['indice', 'ticker', 'nom', 'date_recup'])
        return pd.DataFrame(columns=['ticker', 'roe', 'peg', 'prix', 'date_recup'])

def save_data(df, sheet_name):
    try:
        existing = get_data(sheet_name)
        # Fusion et suppression des doublons sur le ticker
        updated = pd.concat([existing, df], ignore_index=True)
        updated = updated.drop_duplicates(subset=['ticker'], keep='last')
        conn.update(worksheet=sheet_name, data=updated)
        return True
    except Exception as e:
        st.error(f"Erreur de sauvegarde : {e}")
        return False

# --- 3. CHARGEMENT DES DONNÉES ---
df_comp = get_data("index_composition")
today = datetime.now().strftime('%Y-%m-%d')

# --- 4. INTERFACE ---
st.title("🛡️ Screener Stable avec Date de Récupération")

# SECTION 1 : RÉPERTOIRE DES INDICES
with st.expander("📁 Étape 1 : Gérer la composition des indices (Répertoire)"):
    st.write("Cette section remplit votre onglet `index_composition`.")
    
    if st.button("🔄 Actualiser la liste complète (CAC 40 & S&P 500)"):
        with st.spinner("Récupération des listes Wikipedia..."):
            header = {"User-Agent": "Mozilla/5.0"}
            
            # CAC 40
            url_cac = "https://en.wikipedia.org/wiki/CAC_40"
            df_cac = pd.read_html(requests.get(url_cac, headers=header).text)
            df_cac = [t for t in df_cac if 'Ticker' in t.columns][0]
            df_cac = df_cac[['Ticker', 'Company']].rename(columns={'Ticker': 'ticker', 'Company': 'nom'})
            df_cac['indice'] = 'CAC 40'
            df_cac['ticker'] = df_cac['ticker'].apply(lambda x: f"{x}.PA" if ".PA" not in str(x) else x)
            
            # S&P 500
            url_sp = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            df_sp = pd.read_html(requests.get(url_sp, headers=header).text)[0]
            df_sp = df_sp[['Symbol', 'Security']].rename(columns={'Symbol': 'ticker', 'Security': 'nom'})
            df_sp['indice'] = 'S&P 500'
            df_sp['ticker'] = df_sp['ticker'].str.replace('.', '-', regex=True)
            
            final_comp = pd.concat([df_cac, df_sp])
            final_comp['date_recup'] = today  # Date ajoutée ici pour le répertoire
            
            if save_data(final_comp, "index_composition"):
                st.success("Répertoire mis à jour avec succès !")
                st.rerun()

    if not df_comp.empty:
        st.dataframe(df_comp, use_container_width=True, hide_index=True)

# SECTION 2 : RECHERCHE ET ANALYSE
st.divider()
st.subheader("🔍 Étape 2 : Analyse financière à la demande")

if not df_comp.empty:
    c1, c2 = st.columns(2)
    with c1:
        idx = st.selectbox("Choisir l'indice", df_comp['indice'].unique())
    with c2:
        # Filtrage par nom pour faciliter la lecture humaine
        names = df_comp[df_comp['indice'] == idx]['nom'].sort_values().tolist()
        selected_name = st.selectbox("Sélectionner l'action", names)
    
    # Récupération du ticker correspondant
    ticker = df_comp[df_comp['nom'] == selected_name]['ticker'].values[0]
    
    if st.button(f"📊 Lancer l'analyse pour {selected_name}"):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            new_val = pd.DataFrame([{
                "ticker": ticker,
                "roe": round(info.get("returnOnEquity", 0) * 100, 2),
                "peg": info.get("trailingPegRatio", info.get("pegRatio", 0)),
                "prix": info.get("currentPrice", 0),
                "date_recup": today  # Date ajoutée ici pour les données financières
            }])
            
            if save_data(new_val, "stock_data"):
                st.success(f"Données de {ticker} mises à jour au {today}")
        except Exception as e:
            st.error(f"Erreur Yahoo : {e}")

# SECTION 3 : AFFICHAGE DES RÉSULTATS FILTRÉS
st.divider()
df_res = get_data("stock_data")
if not df_res.empty:
    st.subheader("✨ Vos analyses enregistrées")
    # On affiche tout pour vérification, avec la date
    st.dataframe(df_res.sort_values("date_recup", ascending=False), use_container_width=True, hide_index=True)
