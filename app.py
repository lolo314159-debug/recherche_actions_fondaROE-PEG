import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import datetime
import requests

# --- CONFIGURATION ---
st.set_page_config(page_title="Screener Final Stable", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

def get_sheet(name):
    try:
        return conn.read(worksheet=name, ttl=0)
    except:
        return pd.DataFrame()

# --- LOGIQUE DE RÉCUPÉRATION ---
today = datetime.now().strftime('%Y-%m-%d')

st.title("🛡️ Screener Intelligent & Archive Cloud")

# SECTION 1 : RÉPERTOIRE (index_composition)
with st.expander("📁 Étape 1 : Gérer le répertoire des indices"):
    if st.button("🔄 Synchroniser et Nettoyer les Tickers"):
        with st.spinner("Alignement précis des colonnes..."):
            header = {"User-Agent": "Mozilla/5.0"}
            
            # --- CAC 40 (Wikipedia) ---
            r_cac = requests.get("https://en.wikipedia.org/wiki/CAC_40", headers=header)
            df_cac_raw = pd.read_html(r_cac.text)[0]
            # On cherche "Ticker" et "Company" peu importe leur position
            df_cac = pd.DataFrame({
                'ticker': df_cac_raw.filter(like='Ticker').iloc[:, 0],
                'nom': df_cac_raw.filter(like='Company').iloc[:, 0],
                'indice': 'CAC 40'
            })

            # --- S&P 500 (Wikipedia) ---
            r_sp = requests.get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", headers=header)
            df_sp_raw = pd.read_html(r_sp.text)[0]
            # On cherche "Symbol" et "Security"
            df_sp = pd.DataFrame({
                'ticker': df_sp_raw.filter(like='Symbol').iloc[:, 0].str.replace('.', '-', regex=True),
                'nom': df_sp_raw.filter(like='Security').iloc[:, 0],
                'indice': 'S&P 500'
            })

            # --- NETTOYAGE RADICAL ---
            full_comp = pd.concat([df_cac, df_sp])
            # Supprime les tirets "---" : on ne garde que si le ticker contient des lettres
            full_comp = full_comp[full_comp['ticker'].str.contains(r'[A-Za-z]', na=False)]
            full_comp['date_recup'] = today
            
            conn.update(worksheet="index_composition", data=full_comp)
            st.success("Répertoire nettoyé et synchronisé !")
            st.rerun()

# SECTION 2 : ANALYSE À LA DEMANDE
st.divider()
df_comp = get_sheet("index_composition")

if not df_comp.empty:
    st.subheader("🔍 Étape 2 : Analyse financière par ticker")
    col1, col2 = st.columns(2)
    with col1:
        idx = st.selectbox("Indice", df_comp['indice'].unique())
    with col2:
        stocks = df_comp[df_comp['indice'] == idx].sort_values('nom')
        target_nom = st.selectbox("Action", stocks['nom'].tolist())
    
    ticker = stocks[stocks['nom'] == target_nom]['ticker'].values[0]

    if st.button(f"🚀 Analyser {target_nom} ({ticker})"):
        try:
            data = yf.Ticker(ticker).info
            res = pd.DataFrame([{
                "ticker": ticker,
                "roe": round(data.get("returnOnEquity", 0) * 100, 2),
                "peg": data.get("trailingPegRatio", data.get("pegRatio", 0)),
                "prix": data.get("currentPrice", 0),
                "date_recup": today
            }])
            # Sauvegarde dans stock_data
            existing = get_sheet("stock_data")
            updated = pd.concat([existing, res], ignore_index=True).drop_duplicates(subset=['ticker'], keep='last')
            conn.update(worksheet="stock_data", data=updated)
            st.success(f"Données enregistrées pour {target_nom}")
        except Exception as e:
            st.error(f"Erreur Yahoo Finance pour {ticker} : {e}")

# SECTION 3 : AFFICHAGE DES RÉSULTATS
st.divider()
df_res = get_sheet("stock_data")
if not df_res.empty:
    st.subheader("📊 Base de données financières")
    st.dataframe(df_res.sort_values("date_recup", ascending=False), use_container_width=True, hide_index=True)
