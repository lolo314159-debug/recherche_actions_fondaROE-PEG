import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import datetime
import requests
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="Screener Stable", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        return conn.read(worksheet=sheet_name, ttl=0)
    except:
        if sheet_name == "index_composition":
            return pd.DataFrame(columns=['indice', 'ticker', 'nom', 'date_recup'])
        return pd.DataFrame(columns=['ticker', 'roe', 'peg', 'prix', 'date_recup'])

def save_data(df, sheet_name):
    # Nettoyage ultime avant sauvegarde (supprime les tirets seuls)
    if 'ticker' in df.columns:
        df = df[df['ticker'].str.contains(r'[A-Za-z]', na=False)] 
    
    existing = get_data(sheet_name)
    updated = pd.concat([existing, df], ignore_index=True)
    updated = updated.drop_duplicates(subset=['ticker'], keep='last')
    conn.update(worksheet=sheet_name, data=updated)
    return True

# --- LOGIQUE PRINCIPALE ---
today = datetime.now().strftime('%Y-%m-%d')
df_comp = get_data("index_composition")

st.title("🛡️ Correction de la Collecte")

# ETAPE 1 : NETTOYAGE DU RÉPERTOIRE
with st.expander("📁 Étape 1 : Nettoyer le Répertoire des Tickers"):
    if st.button("🧹 Nettoyer et Recharger les Tickers (S&P 500 & CAC 40)"):
        with st.spinner("Nettoyage en cours..."):
            header = {"User-Agent": "Mozilla/5.0"}
            
            # CAC 40
            res_cac = requests.get("https://en.wikipedia.org/wiki/CAC_40", headers=header)
            df_cac = pd.read_html(res_cac.text)[0][['Ticker', 'Company']]
            df_cac.columns = ['ticker', 'nom']
            df_cac['indice'] = 'CAC 40'
            df_cac['ticker'] = df_cac['ticker'].apply(lambda x: f"{x}.PA" if ".PA" not in str(x) else x)
            
            # S&P 500
            res_sp = requests.get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", headers=header)
            df_sp = pd.read_html(res_sp.text)[0][['Symbol', 'Security']]
            df_sp.columns = ['ticker', 'nom']
            df_sp['indice'] = 'S&P 500'
            df_sp['ticker'] = df_sp['ticker'].str.replace('.', '-', regex=True)

            # FUSION ET FILTRE ANTI-TIRETS
            final_comp = pd.concat([df_cac, df_sp])
            # On ne garde que si le ticker contient au moins une lettre (exclut "----")
            final_comp = final_comp[final_comp['ticker'].str.contains(r'[A-Za-z]', na=False)]
            final_comp['date_recup'] = today
            
            # Écrase l'ancien répertoire pollué
            conn.update(worksheet="index_composition", data=final_comp)
            st.success("Répertoire nettoyé ! Les '---' ont été supprimés.")
            st.rerun()

# ETAPE 2 : ANALYSE À LA DEMANDE
st.divider()
if not df_comp.empty:
    st.subheader("🔍 Étape 2 : Lancer une collecte propre")
    # On affiche uniquement les vrais tickers dans la liste
    clean_comp = df_comp[df_comp['ticker'].str.contains(r'[A-Za-z]', na=False)]
    
    selected_stock_nom = st.selectbox("Sélectionner l'entreprise (nom)", clean_comp['nom'].sort_values())
    ticker = clean_comp[clean_comp['nom'] == selected_stock_nom]['ticker'].values[0]
    
    if st.button(f"🚀 Analyser {selected_stock_nom} ({ticker})"):
        try:
            info = yf.Ticker(ticker).info
            new_row = pd.DataFrame([{
                "ticker": ticker,
                "roe": round(info.get("returnOnEquity", 0) * 100, 2),
                "peg": info.get("trailingPegRatio", info.get("pegRatio", 0)),
                "prix": info.get("currentPrice", 0),
                "date_recup": today
            }])
            save_data(new_row, "stock_data")
            st.success(f"Données enregistrées pour {ticker} au {today}")
        except Exception as e:
            st.error(f"Erreur Yahoo pour {ticker}. Vérifiez le symbole.")
