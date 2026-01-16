import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
import time

# 1. CONFIGURATION DE LA PAGE (Doit être la première commande Streamlit)
st.set_page_config(page_title="Screener Fondamental Pro", layout="wide")

# 2. CONNEXION SÉCURISÉE AU CLOUD
conn = st.connection("gsheets", type=GSheetsConnection)

def get_sheet_data():
    try:
        return conn.read(worksheet="stock_data", ttl=0)
    except:
        return pd.DataFrame(columns=['ticker', 'roe', 'peg', 'prix', 'date_recup'])

def save_to_sheet(new_data):
    try:
        existing = get_sheet_data()
        updated = pd.concat([existing, new_data], ignore_index=True)
        updated = updated.drop_duplicates(subset=['ticker', 'date_recup'], keep='last')
        conn.update(worksheet="stock_data", data=updated)
        return True
    except Exception as e:
        if "200" in str(e): return True 
        st.error(f"Erreur d'écriture : {e}")
        return False

# 3. RÉCUPÉRATION DES TICKERS (WIKIPEDIA)
@st.cache_data(ttl=86400)
def get_wiki_tickers(index_name):
    header = {"User-Agent": "Mozilla/5.0"}
    try:
        if index_name == "S&P 500":
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            df = pd.read_html(requests.get(url, headers=header).text)[0]
            return df['Symbol'].str.replace('.', '-', regex=True).tolist()
        else:
            url = "https://en.wikipedia.org/wiki/CAC_40"
            df = [t for t in pd.read_html(requests.get(url, headers=header).text) if 'Ticker' in t.columns][0]
            return [f"{t}.PA" if not str(t).endswith(".PA") else t for t in df['Ticker']]
    except: return []

# 4. INTERFACE ET FILTRES (SIDEBAR)
st.title("🛡️ Screener Intelligent & Archive Cloud")

index_choice = st.sidebar.selectbox("Indice à analyser", ["CAC 40", "S&P 500"])
st.sidebar.header("🎯 Critères de Sélection")
min_roe = st.sidebar.slider("ROE Minimum (%)", 0, 50, 15)
max_peg = st.sidebar.slider("PEG Maximum", 0.0, 5.0, 1.2, step=0.1)

today = datetime.now().strftime('%Y-%m-%d')

# 5. LOGIQUE DE SYNCHRONISATION
wiki_tickers = get_wiki_tickers(index_choice)
stored_df = get_sheet_data()

# Préparation des données numériques pour le filtrage
if not stored_df.empty:
    stored_df['roe'] = pd.to_numeric(stored_df['roe'], errors='coerce')
    stored_df['peg'] = pd.to_numeric(stored_df['peg'], errors='coerce')

# Calcul des manquants
if not stored_df.empty and 'date_recup' in stored_df.columns:
    synced_today = stored_df[stored_df['date_recup'] == today]['ticker'].tolist()
else:
    synced_today = []

missing_tickers = [t for t in wiki_tickers if t not in synced_today]

# Affichage des compteurs
c1, c2, c3 = st.columns(3)
c1.metric("Total Indice", len(wiki_tickers))
c2.metric("Déjà archivés", len(synced_today))
c3.metric("Manquants", len(missing_tickers))

# Bouton de récupération
if len(missing_tickers) > 0:
    if st.button(f"📥 Récupérer les {len(missing_tickers)} manquants"):
        new_records = []
        bar = st.progress(0)
        status = st.empty()
        for i, t in enumerate(missing_tickers):
            try:
                status.text(f"Analyse de {t}...")
                info = yf.Ticker(t).info
                new_records.append({
                    "ticker": t,
                    "roe": round(info.get("returnOnEquity", 0) * 100, 2),
                    "peg": info.get("trailingPegRatio", 0),
                    "prix": info.get("currentPrice", 0),
                    "date_recup": today
                })
                time.sleep(0.4)
                if len(new_records) >= 5:
                    save_to_sheet(pd.DataFrame(new_records))
                    new_records = []
            except: continue
            bar.progress((i + 1) / len(missing_tickers))
        if new_records:
            save_to_sheet(pd.DataFrame(new_records))
        st.rerun()

# 6. AFFICHAGE DES RÉSULTATS FILTRÉS
st.divider()
if not stored_df.empty:
    mask = (stored_df['ticker'].isin(wiki_tickers)) & \
           (stored_df['date_recup'] == today) & \
           (stored_df['roe'] >= min_roe) & \
           (stored_df['peg'] <= max_peg) & \
           (stored_df['peg'] > 0)
    
    filtered_df = stored_df[mask].sort_values("roe", ascending=False)
    
    st.subheader(f"✨ Pépites détectées ({len(filtered_df)})")
    if not filtered_df.empty:
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune action ne correspond à vos critères de filtres actuels.")
