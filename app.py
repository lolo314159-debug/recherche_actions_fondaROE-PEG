import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
import time

# --- 1. CONFIG ET CONNEXION ---
st.set_page_config(page_title="Screener S&P 500", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. FONCTIONS (SANS CHANGEMENT) ---
def get_sheet_data():
    try:
        return conn.read(worksheet="stock_data", ttl=0)
    except:
        return pd.DataFrame(columns=['ticker', 'roe', 'peg', 'prix', 'date_recup'])

def save_to_sheet(new_data):
    try:
        new_data = new_data[new_data['prix'] > 0]
        if new_data.empty: return True
        existing = get_sheet_data()
        updated = pd.concat([existing, new_data], ignore_index=True)
        updated = updated.drop_duplicates(subset=['ticker', 'date_recup'], keep='last')
        conn.update(worksheet="stock_data", data=updated)
        return True
    except:
        return False

# --- 3. LOGIQUE DE CALCUL (DOIT ÊTRE ICI) ---
index_choice = st.sidebar.selectbox("Indice", ["S&P 500", "CAC 40"])
today = datetime.now().strftime('%Y-%m-%d')

# Récupération Wikipedia
header = {"User-Agent": "Mozilla/5.0"}
if index_choice == "S&P 500":
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    wiki_tickers = pd.read_html(requests.get(url, headers=header).text)[0]['Symbol'].str.replace('.', '-', regex=True).tolist()
else:
    url = "https://en.wikipedia.org/wiki/CAC_40"
    df_wiki = [t for t in pd.read_html(requests.get(url, headers=header).text) if 'Ticker' in t.columns][0]
    wiki_tickers = [f"{t}.PA" if not str(t).endswith(".PA") else t for t in df_wiki['Ticker']]

# Comparaison avec la base
stored_df = get_sheet_data()
synced_today = []
if not stored_df.empty and 'date_recup' in stored_df.columns:
    synced_today = stored_df[stored_df['date_recup'] == today]['ticker'].tolist()

# ICI ON DÉFINIT ENFIN LA VARIABLE QUI POSAIT ERREUR
missing_tickers = [t for t in wiki_tickers if t not in synced_today]

# --- 4. INTERFACE ---
st.title("🛡️ Analyse S&P 500 en cours")
c1, c2, c3 = st.columns(3)
c1.metric("Total Indice", len(wiki_tickers))
c2.metric("Déjà en base", len(synced_today))
c3.metric("Restant à scanner", len(missing_tickers))

if len(missing_tickers) > 0:
    if st.button(f"🚀 Lancer le scan des {len(missing_tickers)} actions"):
        new_records = []
        bar = st.progress(0)
        status = st.empty()
        
        for i, t in enumerate(missing_tickers):
            try:
                status.text(f"Extraction Yahoo : {t} ({i+1}/{len(missing_tickers)})")
                info = yf.Ticker(t).info
                p = info.get("currentPrice")
                if p:
                    new_records.append({
                        "ticker": t,
                        "roe": round(info.get("returnOnEquity", 0) * 100, 2),
                        "peg": info.get("trailingPegRatio", info.get("pegRatio", 0)),
                        "prix": p,
                        "date_recup": today
                    })
                
                # Sauvegarde par mini-blocs de 5 pour voir le Sheet se remplir
                if len(new_records) >= 5:
                    save_to_sheet(pd.DataFrame(new_records))
                    new_records = []
                time.sleep(0.4)
            except:
                continue
            bar.progress((i + 1) / len(missing_tickers))
        
        if new_records:
            save_to_sheet(pd.DataFrame(new_records))
        st.rerun()
