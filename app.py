import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import datetime
import time

st.set_page_config(page_title="Scanner Finance - Cloud Save", layout="wide")

# --- CONNEXION GOOGLE SHEETS ---
# Note : L'URL doit être configurée dans .streamlit/secrets.toml ou passée directement
url = "VOTRE_URL_GOOGLE_SHEET_ICI"
conn = st.connection("gsheets", type=GSheetsConnection)

def get_stored_data(worksheet_name):
    try:
        return conn.read(spreadsheet=url, worksheet=worksheet_name)
    except:
        return pd.DataFrame()

def save_to_sheet(df, worksheet_name):
    existing_data = get_stored_data(worksheet_name)
    updated_data = pd.concat([existing_data, df], ignore_index=True).drop_duplicates()
    conn.update(spreadsheet=url, worksheet=worksheet_name, data=updated_data)

# --- LOGIQUE DE RÉCUPÉRATION ---
@st.cache_data(ttl=3600)
def fetch_and_save_stock(ticker):
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Vérifier si on a déjà la donnée du jour dans le Sheet
    stored_stocks = get_stored_data("stock_data")
    if not stored_stocks.empty:
        match = stored_stocks[(stored_stocks['ticker'] == ticker) & (stored_stocks['date_recup'] == today)]
        if not match.empty:
            return match.iloc[0].to_dict()

    # Sinon, appel Yahoo Finance
    try:
        s = yf.Ticker(ticker)
        info = s.info
        new_data = {
            "ticker": ticker,
            "roe": round(info.get("returnOnEquity", 0) * 100, 2),
            "peg": info.get("trailingPegRatio", info.get("pegRatio", 0)),
            "prix": info.get("currentPrice", 0),
            "date_recup": today
        }
        # Sauvegarde immédiate dans le Sheet
        save_to_sheet(pd.DataFrame([new_data]), "stock_data")
        return new_data
    except:
        return None

# --- INTERFACE ---
st.title("📈 Screener avec Sauvegarde Google Sheets")

index_choice = st.sidebar.selectbox("Indice", ["CAC 40", "S&P 500"])

# 1. Gestion de la composition (simplifiée pour l'exemple)
if st.button("Actualiser la liste des actions"):
    # Ici vous mettriez votre fonction Wikipedia habituelle
    # Puis save_to_sheet(df, "index_composition")
    st.info("Liste mise à jour (simulation)")

# 2. Analyse et archivage automatique
st.subheader("Analyse d'une action")
ticker_to_scan = st.text_input("Entrez un ticker (ex: MC.PA, TSLA)").upper()

if ticker_to_scan:
    with st.spinner("Recherche et archivage..."):
        data = fetch_and_save_stock(ticker_to_scan)
        if data:
            st.write(f"### Données pour {ticker_to_scan}")
            col1, col2, col3 = st.columns(3)
            col1.metric("ROE", f"{data['roe']}%")
            col2.metric("PEG", data['peg'])
            col3.metric("Prix", data['prix'])
            st.success(f"Donnée archivée dans Google Sheets à la date du {data['date_recup']}")
        else:
            st.error("Erreur Yahoo Finance (Blocage ou Ticker invalide)")

# 3. Affichage de l'archive
if st.checkbox("Afficher l'historique complet du Google Sheet"):
    st.dataframe(get_stored_data("stock_data"))
