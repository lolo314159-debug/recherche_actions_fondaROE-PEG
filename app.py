import streamlit as st
import yfinance as yf
import pandas as pd

# Configuration de la page
st.set_page_config(page_title="Fin-Scanner Online", layout="wide")

# --- FONCTION DE RÉCUPÉRATION AVEC CACHE ---
@st.cache_data(ttl=3600)  # Garde les données en mémoire 1 heure
def load_data(tickers):
    results = []
    for t in tickers:
        try:
            s = yf.Ticker(t)
            info = s.info
            results.append({
                "Ticker": t,
                "Nom": info.get("shortName"),
                "ROE": info.get("returnOnEquity", 0),
                "PEG": info.get("trailingPegRatio", 0),
                "Secteur": info.get("sector")
            })
        except:
            continue
    return pd.DataFrame(results)

# --- INTERFACE ---
st.title("🚀 Screener Fondamental en Ligne")

# Listes d'actions par zone
MARKETS = {
    "USA (S&P500)": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "BRK-B"],
    "France (CAC40)": ["MC.PA", "OR.PA", "TTE.PA", "SAN.PA", "AIR.PA", "RMS.PA"],
    "Europe (Mix)": ["ASML", "SAP", "NVO", "SIE.DE", "IDEXY"]
}

with st.sidebar:
    st.header("Paramètres")
    zone = st.selectbox("Choisir une zone", list(MARKETS.keys()))
    roe_min = st.number_input("ROE Minimum (ex: 0.15 pour 15%)", value=0.15)
    peg_max = st.number_input("PEG Maximum", value=1.5)
    
    st.divider()
    ticker_input = st.text_input("Recherche rapide (ex: TSLA)").upper()

# --- LOGIQUE ---
data_load_state = st.text('Chargement des données du marché...')
df = load_data(MARKETS[zone])
data_load_state.empty()

# Filtrage
filtered_df = df[(df['ROE'] >= roe_min) & (df['PEG'] <= peg_max) & (df['PEG'] > 0)]

# Affichage
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"Résultats pour {zone}")
    st.dataframe(filtered_df, use_container_width=True)

with col2:
    if ticker_input:
        st.subheader(f"Focus : {ticker_input}")
        single_data = load_data([ticker_input])
        st.write(single_data)
