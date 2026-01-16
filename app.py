import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Screener Dynamique", layout="wide")

# --- ÉTAPE 1 : RÉCUPÉRATION DYNAMIQUE DES TICKERS ---
@st.cache_data(ttl=86400) # Mise à jour une fois par 24h
def get_index_tickers(index_name):
    if index_name == "S&P 500":
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        # On cherche la table qui contient la colonne 'Symbol'
        tables = pd.read_html(url)
        df = [t for t in tables if 'Symbol' in t.columns][0]
        return df['Symbol'].str.replace('.', '-', regex=True).tolist()
    
    elif index_name == "CAC 40":
        url = "https://en.wikipedia.org/wiki/CAC_40"
        # On cherche la table qui contient la colonne 'Ticker'
        tables = pd.read_html(url)
        df = [t for t in tables if 'Ticker' in t.columns][0]
        tickers = df['Ticker'].tolist()
        return [t if t.endswith(".PA") else f"{t}.PA" for t in tickers]
    return []
# --- ÉTAPE 2 : TÉLÉCHARGEMENT DES DONNÉES FONDAMENTALES ---
@st.cache_data(ttl=3600)
def fetch_fundamental_data(tickers):
    data_list = []
    progress_bar = st.progress(0)
    for i, ticker in enumerate(tickers):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            data_list.append({
                "Ticker": ticker,
                "Nom": info.get("longName"),
                "ROE (%)": info.get("returnOnEquity", 0) * 100,
                "PEG": info.get("trailingPegRatio", info.get("pegRatio", 0)),
                "Secteur": info.get("sector"),
                "Prix": info.get("currentPrice")
            })
        except:
            continue
        progress_bar.progress((i + 1) / len(tickers))
    return pd.DataFrame(data_list)

# --- INTERFACE UTILISATEUR ---
st.title("🔍 Screener Fondamental (Live Index)")

with st.sidebar:
    st.header("Filtres")
    selected_index = st.selectbox("Indice à scanner", ["CAC 40", "S&P 500"])
    min_roe = st.slider("ROE Minimum (%)", 0, 50, 15)
    max_peg = st.slider("PEG Maximum", 0.0, 3.0, 1.2)
    
    if st.button("🔄 Forcer la mise à jour"):
        st.cache_data.clear()
        st.rerun()

# Logique de calcul
tickers = get_index_tickers(selected_index)
st.info(f"Composants détectés pour {selected_index} : {len(tickers)}")

df = fetch_fundamental_data(tickers)

# Filtrage
filtered_df = df[(df["ROE (%)"] >= min_roe) & (df["PEG"] <= max_peg) & (df["PEG"] > 0)]

st.subheader(f"Résultats du filtrage ({len(filtered_df)} actions)")
st.dataframe(filtered_df.sort_values("ROE (%)", ascending=False), use_container_width=True)
