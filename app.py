import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="Screener Public Cloud", layout="wide")

# --- CONNEXION SIMPLE ---
# Remplace par l'URL de ton sheet partagé en "Éditeur"
URL_SHEET = "REMPLACE_PAR_TON_LIEN_GOOGLE_SHEET"

conn = st.connection("gsheets", type=GSheetsConnection)

def load_archive():
    try:
        # Lit la feuille "stock_data"
        return conn.read(spreadsheet=URL_SHEET, worksheet="stock_data")
    except:
        # Si la feuille est vide ou n'existe pas encore
        return pd.DataFrame(columns=["ticker", "nom", "roe", "peg", "prix", "date_recup"])

def save_data(new_row_df):
    existing = load_archive()
    # On ajoute la nouvelle ligne et on enlève les doublons (même ticker, même jour)
    updated = pd.concat([existing, new_row_df], ignore_index=True)
    updated = updated.drop_duplicates(subset=['ticker', 'date_recup'], keep='last')
    
    # On renvoie tout vers Google Sheets
    conn.update(spreadsheet=URL_SHEET, worksheet="stock_data", data=updated)
    st.cache_data.clear()

# --- INTERFACE ---
st.title("🚀 Screener Fondamental (Mode Public)")
st.info("Données sauvegardées sur Google Sheets sans compte de service.")

ticker = st.text_input("Rechercher un Ticker (ex: MC.PA, ASML, NVDA)", "").upper()

if ticker:
    today = datetime.now().strftime('%Y-%m-%d')
    archive = load_archive()
    
    # Vérification dans l'archive
    match = archive[(archive['ticker'] == ticker) & (archive['date_recup'] == today)]
    
    if not match.empty:
        st.success(f"Donnée récupérée depuis l'archive (Date: {today})")
        data = match.iloc[0].to_dict()
    else:
        with st.spinner(f"Appel Yahoo Finance pour {ticker}..."):
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                data = {
                    "ticker": ticker,
                    "nom": info.get("longName", "N/A"),
                    "roe": round(info.get("returnOnEquity", 0) * 100, 2),
                    "peg": info.get("trailingPegRatio", info.get("pegRatio", 0)),
                    "prix": info.get("currentPrice", 0),
                    "date_recup": today
                }
                # Sauvegarde auto
                save_data(pd.DataFrame([data]))
            except:
                st.error("Erreur Yahoo (Ticker invalide ou blocage).")
                data = None

    if data:
        c1, c2, c3 = st.columns(3)
        c1.metric("ROE (%)", f"{data['roe']}%")
        c2.metric("PEG Ratio", data['peg'])
        c3.metric("Prix", f"{data['prix']}")

st.divider()
if st.checkbox("Afficher la base de données (Google Sheets)"):
    st.dataframe(load_archive(), use_container_width=True)
