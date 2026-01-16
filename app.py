import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
import time

# 1. CONFIGURATION (Doit être en haut)
st.set_page_config(page_title="Screener Pro S&P 500", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. FONCTIONS DE BASE
def get_sheet_data():
    try:
        return conn.read(worksheet="stock_data", ttl=0)
    except:
        return pd.DataFrame(columns=['ticker', 'roe', 'peg', 'prix', 'date_recup'])

def save_to_sheet(new_data):
    try:
        # Nettoyage strict pour éviter les lignes "0" (image_2e4fec.png)
        new_data = new_data[new_data['prix'] > 0]
        if new_data.empty: return True
        
        existing = get_sheet_data()
        updated = pd.concat([existing, new_data], ignore_index=True)
        # Supprime les doublons pour ne pas alourdir le fichier
        updated = updated.drop_duplicates(subset=['ticker', 'date_recup'], keep='last')
        conn.update(worksheet="stock_data", data=updated)
        return True
    except Exception as e:
        if "200" in str(e): return True
        return False

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

# 3. INTERFACE ET LOGIQUE
st.title("🛡️ Screener Intelligent & Archive Cloud")
index_choice = st.sidebar.selectbox("Indice", ["S&P 500", "CAC 40"])
today = datetime.now().strftime('%Y-%m-%d')

# --- DEFINITION DES VARIABLES (Règle l'erreur image_2e5710.png) ---
wiki_tickers = get_wiki_tickers(index_choice)
stored_df = get_sheet_data()

synced_today = []
if not stored_df.empty and 'date_recup' in stored_df.columns:
    synced_today = stored_df[stored_df['date_recup'] == today]['ticker'].tolist()

missing_tickers = [t for t in wiki_tickers if t not in synced_today]

# 4. AFFICHAGE DES METRICS
c1, c2, c3 = st.columns(3)
c1.metric(f"Total {index_choice}", len(wiki_tickers))
c2.metric("En Base (Aujourd'hui)", len(synced_today))
c3.metric("À récupérer", len(missing_tickers))

# 5. BOUCLE DE RÉCUPÉRATION SÉCURISÉE
if len(missing_tickers) > 0:
    if st.button(f"📥 Lancer la récupération"):
        new_records = []
        bar = st.progress(0)
        status = st.empty()
        
        for i, t in enumerate(missing_tickers):
            try:
                # On évite les tickers invalides comme "---" (image_2e4c63.png)
                if len(t) < 2 or t.startswith("-"): continue
                
                status.text(f"Analyse de {t} ({i+1}/{len(missing_tickers)})...")
                info = yf.Ticker(t).info
                price = info.get("currentPrice")
                
                if price and price > 0:
                    new_records.append({
                        "ticker": t,
                        "roe": round(info.get("returnOnEquity", 0) * 100, 2),
                        "peg": info.get("trailingPegRatio", info.get("pegRatio", 0)),
                        "prix": price,
                        "date_recup": today
                    })
                
                # SAUVEGARDE PAR BLOCS (Crucial pour ne rien perdre)
                if len(new_records) >= 5:
                    save_to_sheet(pd.DataFrame(new_records))
                    new_records = []
                
                time.sleep(0.4) 
            except: continue
            bar.progress((i + 1) / len(missing_tickers))
        
        if new_records:
            save_to_sheet(pd.DataFrame(new_records))
        st.success("Terminé !")
        st.rerun()

# 6. AFFICHAGE DU TABLEAU
st.divider()
if not stored_df.empty:
    mask = (stored_df['ticker'].isin(wiki_tickers)) & (stored_df['date_recup'] == today)
    display_df = stored_df[mask].sort_values("roe", ascending=False)
    st.subheader(f"✨ Résultats {index_choice}")
    st.dataframe(display_df, use_container_width=True, hide_index=True)
