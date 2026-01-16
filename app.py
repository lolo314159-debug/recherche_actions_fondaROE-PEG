import streamlit as st
import pandas as pd
import yfinance as yf
import requests

st.set_page_config(page_title="Scanner de Qualité", layout="wide")

# --- FONCTION LISTE (WIKIPEDIA) ---
@st.cache_data(ttl=86400)
def get_tickers(index_name):
    header = {"User-Agent": "Mozilla/5.0"}
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies" if index_name == "S&P 500" else "https://en.wikipedia.org/wiki/CAC_40"
    res = requests.get(url, headers=header)
    tables = pd.read_html(res.text)
    df = [t for t in tables if any(col in t.columns for col in ['Symbol', 'Ticker'])][0]
    col = 'Symbol' if 'Symbol' in df.columns else 'Ticker'
    tickers = df[col].str.replace('.', '-', regex=True).tolist()
    return [f"{t}.PA" if index_name == "CAC 40" and not str(t).endswith(".PA") else t for t in tickers]

# --- FONCTION DONNÉES (UNIFIEE) ---
def get_single_stock_data(ticker):
    try:
        # On n'utilise pas de session ici pour laisser yfinance gérer le fallback
        s = yf.Ticker(ticker)
        info = s.info
        return {
            "Ticker": ticker,
            "Nom": info.get("longName", "N/A"),
            "ROE (%)": info.get("returnOnEquity", 0) * 100,
            "PEG": info.get("trailingPegRatio", info.get("pegRatio", 0)),
            "Secteur": info.get("sector", "N/A")
        }
    except:
        return None

# --- INTERFACE ---
st.title("🛡️ Scanner Fondamental (Mode Sécurisé)")

index_choice = st.sidebar.selectbox("Indice", ["CAC 40", "S&P 500"])
tickers = get_tickers(index_choice)

# Recherche spécifique (Prioritaire pour éviter le ban)
st.subheader("🔍 Recherche rapide par Action")
manual_search = st.text_input("Entrez un Ticker (ex: MC.PA, AAPL, MSFT)", "").upper()

if manual_search:
    data = get_single_stock_data(manual_search)
    if data:
        st.success(f"Données trouvées pour {manual_search}")
        st.table(pd.DataFrame([data]))
    else:
        st.error("Impossible de récupérer les données pour ce ticker.")

st.divider()

# Screening assisté
st.subheader(f"📋 Liste des composants {index_choice}")
st.write("Pour éviter le blocage de Yahoo, sélectionnez une action pour voir ses détails :")
selected_tick = st.selectbox("Sélectionnez une action de la liste", [""] + tickers)

if selected_tick:
    with st.spinner(f"Chargement de {selected_tick}..."):
        res = get_single_stock_data(selected_tick)
        if res:
            st.json(res)
