import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
import time

st.set_page_config(page_title="Screener Multi-Indice", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

def get_sheet_data():
    try:
        return conn.read(worksheet="stock_data", ttl=0)
    except:
        return pd.DataFrame(columns=['ticker', 'roe', 'peg', 'prix', 'date_recup'])

def save_to_sheet(new_data):
    try:
        # On ne garde que les données valides (prix > 0)
        new_data = new_data[new_data['prix'] > 0]
        if new_data.empty: return True
        
        existing = get_sheet_data()
        updated = pd.concat([existing, new_data], ignore_index=True)
        updated = updated.drop_duplicates(subset=['ticker', 'date_recup'], keep='last')
        conn.update(worksheet="stock_data", data=updated)
        return True
    except Exception as e:
        if "200" in str(e): return True
        return False

@st.cache_data(ttl=86400)
def get_wiki_tickers(index_name):
    header = {"User-Agent": "Mozilla/5.0"}
    if index_name == "S&P 500":
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        df = pd.read_html(requests.get(url, headers=header).text)[0]
        # Yahoo Finance utilise des tirets pour les classes d'actions US (ex: BRK-B)
        return df['Symbol'].str.replace('.', '-', regex=True).tolist()
    else:
        url = "https://en.wikipedia.org/wiki/CAC_40"
        df = [t for t in pd.read_html(requests.get(url, headers=header).text) if 'Ticker' in t.columns][0]
        return [f"{t}.PA" if not str(t).endswith(".PA") else t for t in df['Ticker']]

st.title("🛡️ Screener Intelligent & Archive Cloud")
index_choice = st.sidebar.selectbox("Indice", ["S&P 500", "CAC 40"])
st.sidebar.header("🎯 Filtres")
min_roe = st.sidebar.slider("ROE Min (%)", 0, 50, 15)
max_peg = st.sidebar.slider("PEG Max", 0.0, 5.0, 1.2, step=0.1)

today = datetime.now().strftime('%Y-%m-%d')
wiki_tickers = get_wiki_tickers(index_choice)
stored_df = get_sheet_data()

# Identification des manquants spécifiques à l'indice choisi
synced_today = []
if not stored_df.empty and 'date_recup' in stored_df.columns:
    synced_today = stored_df[stored_df['date_recup'] == today]['ticker'].tolist()

missing_tickers = [t for t in wiki_tickers if t not in synced_today]

c1, c2, c3 = st.columns(3)
c1.metric(f"Total {index_choice}", len(wiki_tickers))
c2.metric("En Base (Aujourd'hui)", len(synced_today))
c3.metric("À récupérer", len(missing_tickers))

if len(missing_tickers) > 0:
    if st.button(f"📥 Lancer la récupération de {len(missing_tickers)} tickers"):
        new_records = []
        bar = st.progress(0)
        status = st.empty()
        
        for i, t in enumerate(missing_tickers):
            try:
                status.text(f"Analyse de {t} ({i+1}/{len(missing_tickers)})...")
                stock = yf.Ticker(t)
                info = stock.info
                price = info.get("currentPrice")
                
                if price and price > 0:
                    new_records.append({
                        "ticker": t,
                        "roe": round(info.get("returnOnEquity", 0) * 100, 2),
                        "peg": info.get("trailingPegRatio", info.get("pegRatio", 0)),
                        "prix": price,
                        "date_recup": today
                    })
                
                # Sauvegarde auto toutes les 10 actions
                if len(new_records) >= 10:
                    save_to_sheet(pd.DataFrame(new_records))
                    new_records = []
                
                time.sleep(0.4) 
            except:
                continue # C'est ce bloc qui corrige l'erreur de syntaxe !
            
            bar.progress((i + 1) / len(missing_tickers))
        
        if new_records:
            save_to_sheet(pd.DataFrame(new_records))
        st.success("Synchronisation terminée !")
        st.rerun()

st.divider()
if not stored_df.empty:
    # Nettoyage pour les filtres
    stored_df['roe'] = pd.to_numeric(stored_df['roe'], errors='coerce')
    stored_df['peg'] = pd.to_numeric(stored_df['peg'], errors='coerce')
    
    # On n'affiche que les actions de l'indice sélectionné
    mask = (stored_df['ticker'].isin(wiki_tickers)) & \
           (stored_df['date_recup'] == today) & \
           (stored_df['roe'] >= min_roe) & \
           (stored_df['peg'] <= max_peg) & (stored_df['peg'] > 0)
    
    filt_df = stored_df[mask].sort_values("roe", ascending=False)
    st.subheader(f"✨ Résultats {index_choice} ({len(filt_df)})")
    st.dataframe(filt_df, use_container_width=True, hide_index=True)
