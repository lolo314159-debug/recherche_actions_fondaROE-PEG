import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
import time

st.set_page_config(page_title="Screener Auto-Update", layout="wide")

# URL de ton Google Sheet (Partagé en éditeur)
URL_SHEET = "REMPLACE_PAR_TON_LIEN_GOOGLE_SHEET"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FONCTIONS DE RÉCUPÉRATION ---

@st.cache_data(ttl=3600)
def get_wiki_tickers(index_name):
    """Récupère la liste officielle actuelle sur Wikipedia"""
    header = {"User-Agent": "Mozilla/5.0"}
    if index_name == "S&P 500":
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        res = requests.get(url, headers=header)
        df = pd.read_html(res.text)[0]
        tickers = df['Symbol'].str.replace('.', '-', regex=True).tolist()
    else:
        url = "https://en.wikipedia.org/wiki/CAC_40"
        res = requests.get(url, headers=header)
        df = [t for t in pd.read_html(res.text) if 'Ticker' in t.columns][0]
        tickers = [f"{t}.PA" if not str(t).endswith(".PA") else t for t in df['Ticker']]
    return tickers

def get_sheet_data(worksheet):
    try:
        return conn.read(spreadsheet=URL_SHEET, worksheet=worksheet)
    except:
        return pd.DataFrame()

# --- LOGIQUE DE MISE À JOUR ---

st.title("🛡️ Screener Intelligent & Archive Cloud")

index_choice = st.sidebar.selectbox("Indice à surveiller", ["CAC 40", "S&P 500"])
today = datetime.now().strftime('%Y-%m-%d')

# 1. État des lieux
with st.spinner("Vérification de la base de données..."):
    wiki_tickers = get_wiki_tickers(index_choice)
    stored_data = get_sheet_data("stock_data")
    
    # Filtrer les données déjà présentes aujourd'hui
    if not stored_data.empty and 'date_recup' in stored_data.columns:
        already_synced = stored_data[stored_data['date_recup'] == today]['ticker'].tolist()
    else:
        already_synced = []

    missing_tickers = [t for t in wiki_tickers if t not in already_synced]

# 2. Affichage des compteurs
col1, col2, col3 = st.columns(3)
col1.metric("Total Indice", len(wiki_tickers))
col2.metric("Déjà en Base", len(already_synced))
col3.metric("Manquants", len(missing_tickers))

# 3. Action : Récupérer les manquants
if len(missing_tickers) > 0:
    if st.button(f"📥 Récupérer les {len(missing_tickers)} manquants sur Yahoo"):
        new_entries = []
        progress_bar = st.progress(0)
        status = st.empty()
        
        for i, t in enumerate(missing_tickers):
            try:
                status.text(f"Récupération de {t}...")
                s = yf.Ticker(t)
                info = s.info
                new_entries.append({
                    "ticker": t,
                    "roe": round(info.get("returnOnEquity", 0) * 100, 2),
                    "peg": info.get("trailingPegRatio", info.get("pegRatio", 0)),
                    "prix": info.get("currentPrice", 0),
                    "date_recup": today
                })
                time.sleep(0.5) # Sécurité anti-blocage
            except:
                continue
            progress_bar.progress((i + 1) / len(missing_tickers))
        
        if new_entries:
            df_new = pd.DataFrame(new_entries)
            updated_df = pd.concat([stored_data, df_new], ignore_index=True)
            conn.update(spreadsheet=URL_SHEET, worksheet="stock_data", data=updated_df)
            st.success("Base de données mise à jour !")
            st.rerun()

# 4. Affichage du tableau final filtrable
st.divider()
if not stored_data.empty:
    st.subheader(f"Analyse des données disponibles ({index_choice})")
    # On affiche uniquement les données de l'indice sélectionné
    df_display = stored_data[stored_data['ticker'].isin(wiki_tickers) & (stored_data['date_recup'] == today)]
    
    # Filtres interactifs
    roe_min = st.slider("ROE Min (%)", 0, 50, 15)
    df_filtered = df_display[df_display['roe'] >= roe_min]
    
    st.dataframe(df_filtered.sort_values("roe", ascending=False), use_container_width=True)
