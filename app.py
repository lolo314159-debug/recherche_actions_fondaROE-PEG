import streamlit as st
import pandas as pd
import yfinance as yf
import requests

st.set_page_config(page_title="Scanner de Qualité", layout="wide")

# Configuration de la session pour éviter le blocage Yahoo
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
})

@st.cache_data(ttl=86400)
def get_index_tickers(index_name):
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies" if index_name == "S&P 500" else "https://en.wikipedia.org/wiki/CAC_40"
    res = session.get(url)
    tables = pd.read_html(res.text)
    if index_name == "S&P 500":
        df = [t for t in tables if 'Symbol' in t.columns][0]
        return df['Symbol'].str.replace('.', '-', regex=True).tolist()[:50] # On limite à 50 pour le test
    else:
        df = [t for t in tables if 'Ticker' in t.columns][0]
        return [f"{t}.PA" if not str(t).endswith(".PA") else t for t in df['Ticker']]

@st.cache_data(ttl=3600)
def fetch_data(tickers):
    results = []
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    for i, t in enumerate(tickers):
        try:
            status_text.text(f"Analyse de : {t}...")
            # On passe la session ici pour contourner le blocage
            s = yf.Ticker(t, session=session) 
            info = s.info
            results.append({
                "Ticker": t,
                "Nom": info.get("longName", "N/A"),
                "ROE (%)": info.get("returnOnEquity", 0) * 100,
                "PEG": info.get("trailingPegRatio", info.get("pegRatio", 0)),
                "Secteur": info.get("sector", "N/A")
            })
        except Exception:
            continue
        progress_bar.progress((i + 1) / len(tickers))
    
    status_text.empty()
    progress_bar.empty()
    return pd.DataFrame(results)

# --- INTERFACE ---
st.title("🔍 Scanner de Qualité Financière")

with st.sidebar:
    index_choice = st.selectbox("Indice", ["CAC 40", "S&P 500"])
    min_roe = st.slider("ROE Min (%)", 0, 50, 15)
    max_peg = st.slider("PEG Max", 0.0, 3.0, 1.5)
    if st.button("Réinitialiser le Cache"):
        st.cache_data.clear()

# Exécution
with st.spinner("Récupération de la liste des actions..."):
    tickers = get_index_tickers(index_choice)

df = fetch_data(tickers)

if not df.empty:
    # Filtrage
    mask = (df["ROE (%)"] >= min_roe) & (df["PEG"] <= max_peg) & (df["PEG"] > 0)
    filtered_df = df[mask]
    
    st.subheader(f"Résultats ({len(filtered_df)} actions)")
    st.dataframe(filtered_df.sort_values("ROE (%)", ascending=False), use_container_width=True)
else:
    st.warning("⚠️ Yahoo Finance bloque temporairement la requête. Réessayez dans quelques minutes ou réduisez la liste.")
