import streamlit as st
import pandas as pd
import yfinance as yf
import requests

st.set_page_config(page_title="Screener Pro", layout="wide")

# --- RÉCUPÉRATION DES TICKERS ---
@st.cache_data(ttl=86400)
def get_index_tickers(index_name):
    header = {"User-Agent": "Mozilla/5.0"}
    if index_name == "S&P 500":
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        res = requests.get(url, headers=header)
        df = pd.read_html(res.text)[0]
        return df['Symbol'].str.replace('.', '-', regex=True).tolist()
    else:
        url = "https://en.wikipedia.org/wiki/CAC_40"
        res = requests.get(url, headers=header)
        tables = pd.read_html(res.text)
        df = [t for t in tables if 'Ticker' in t.columns][0]
        return [f"{t}.PA" if not str(t).endswith(".PA") else t for t in df['Ticker']]

# --- RÉCUPÉRATION DES DONNÉES ---
@st.cache_data(ttl=3600)
def fetch_data(tickers):
    results = []
    progress_bar = st.progress(0)
    for i, t in enumerate(tickers):
        try:
            s = yf.Ticker(t)
            info = s.info
            results.append({
                "Ticker": t,
                "Nom": info.get("longName", "N/A"),
                "ROE (%)": info.get("returnOnEquity", 0) * 100,
                "PEG": info.get("trailingPegRatio", info.get("pegRatio", 0)),
                "Secteur": info.get("sector", "N/A")
            })
        except:
            continue
        progress_bar.progress((i + 1) / len(tickers))
    progress_bar.empty()
    return pd.DataFrame(results)

# --- INTERFACE ---
st.title("🔍 Scanner de Qualité Financière")

with st.sidebar:
    index_choice = st.selectbox("Indice", ["CAC 40", "S&P 500"])
    min_roe = st.slider("ROE Min (%)", 0, 50, 15)
    max_peg = st.slider("PEG Max", 0.0, 3.0, 1.5)
    st.divider()
    search = st.text_input("Recherche Ticker (ex: AAPL)").upper()

# Exécution
tickers = get_index_tickers(index_choice)
df = fetch_data(tickers)

if not df.empty:
    # Sécurité pour la KeyError
    mask = (df["ROE (%)"] >= min_roe) & (df["PEG"] <= max_peg) & (df["PEG"] > 0)
    filtered_df = df[mask]
    
    if search:
        st.subheader(f"Résultat pour {search}")
        st.write(fetch_data([search]))
    
    st.subheader(f"Actions filtrées ({len(filtered_df)})")
    st.dataframe(filtered_df.sort_values("ROE (%)", ascending=False), use_container_width=True)
else:
    st.error("Impossible de récupérer les données financières.")
