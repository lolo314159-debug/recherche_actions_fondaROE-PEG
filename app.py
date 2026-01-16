import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
import time

st.set_page_config(page_title="Screener Fondamental Pro", layout="wide")

# --- CONNEXION SÉCURISÉE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_sheet_data():
    try:
        # Lecture en temps réel (ttl=0) de l'onglet stock_data
        return conn.read(worksheet="stock_data", ttl=0)
    except:
        return pd.DataFrame(columns=['ticker', 'roe', 'peg', 'prix', 'date_recup'])

def save_to_sheet(new_data):
    try:
        existing = get_sheet_data()
        updated = pd.concat([existing, new_data], ignore_index=True)
        # On garde la dernière valeur en cas de doublon (ticker + date)
        updated = updated.drop_duplicates(subset=['ticker', 'date_recup'], keep='last')
        conn.update(worksheet="stock_data", data=updated)
        return True
    except Exception as e:
        if "200" in str(e): return True # Ignore l'erreur de formatage si l'écriture a réussi
        st.error(f"Erreur d'écriture : {e}")
        return False

# --- RÉCUPÉRATION TICKERS (WIKIPEDIA) ---
@st.cache_data(ttl=86400)
def get_wiki_tickers(index_name):
    header = {"User-Agent": "Mozilla/5.0"}
    if index_name == "S&P 500":
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        df = pd.read_html(requests.get(url, headers=header).text)[0]
        return df['Symbol'].str.replace('.', '-', regex=True).tolist()
    else:
        url = "https://en.wikipedia.org/wiki/CAC_40"
        df = [t for t in pd.read_html(requests.get(url, headers=header).text) if 'Ticker' in t.columns][0]
        return [f"{t}.PA" if not str(t).endswith(".PA") else t for t in df['Ticker']]

# --- INTERFACE PRINCIPALE ---
st.title("🛡️ Screener Intelligent & Archive Cloud")

index_choice = st.sidebar.selectbox("Indice à analyser", ["CAC 40", "S&P 500"])
today = datetime.now().strftime('%Y-%m-%d')

# 1. Audit de la base de données
wiki_tickers = get_wiki_tickers(index_choice)
stored_df = get_sheet_data()

if not stored_df.empty and 'date_recup' in stored_df.columns:
    synced_today = stored_df[stored_df['date_recup'] == today]['ticker'].tolist()
else:
    synced_today = []

missing_tickers = [t for t in wiki_tickers if t not in synced_today]

# 2. Affichage des statistiques
c1, c2, c3 = st.columns(3)
c1.metric("Total Indice", len(wiki_tickers))
c2.metric("Déjà archivés (Aujourd'hui)", len(synced_today))
c3.metric("Manquants", len(missing_tickers))

# 3. Action de récupération
if len(missing_tickers) > 0:
    if st.button(f"📥 Récupérer les {len(missing_tickers)} manquants sur Yahoo"):
        new_records = []
        bar = st.progress(0)
        status = st.empty()
        
        for i, t in enumerate(missing_tickers):
            try:
                status.text(f"Récupération de {t}...")
                info = yf.Ticker(t).info
                new_records.append({
                    "ticker": t,
                    "roe": round(info.get("returnOnEquity", 0) * 100, 2),
                    "peg": info.get("trailingPegRatio", 0),
                    "prix": info.get("currentPrice", 0),
                    "date_recup": today
                })
                time.sleep(0.5) # Sécurité pour Yahoo
                
                # Sauvegarde par blocs de 5 pour la stabilité
                if len(new_records) >= 5:
                    save_to_sheet(pd.DataFrame(new_records))
                    new_records = []
            except:
                continue
            bar.progress((i + 1) / len(missing_tickers))
        
        if new_records:
            save_to_sheet(pd.DataFrame(new_records))
        st.rerun()

# 4. Affichage des données
st.divider()
if not stored_df.empty:
    # On affiche uniquement les données de l'indice sélectionné pour aujourd'hui
    display_df = stored_df[(stored_df['ticker'].isin(wiki_tickers)) & (stored_df['date_recup'] == today)]
    st.subheader(f"Données du jour : {index_choice}")
    st.dataframe(display_df.sort_values("roe", ascending=False), use_container_width=True, hide_index=True)
