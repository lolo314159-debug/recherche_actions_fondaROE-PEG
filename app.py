import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time

st.set_page_config(page_title="Scanner de Qualité", layout="wide")

# --- CONFIGURATION SESSION ---
def get_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    })
    return session

# --- RÉCUPÉRATION DES TICKERS ---
@st.cache_data(ttl=86400)
def get_index_tickers(index_name):
    session = get_session()
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies" if index_name == "S&P 500" else "https://en.wikipedia.org/wiki/CAC_40"
    res = session.get(url)
    tables = pd.read_html(res.text)
    if index_name == "S&P 500":
        df = [t for t in tables if 'Symbol' in t.columns][0]
        # On limite volontairement à 40 pour éviter le bannissement immédiat sur Cloud
        return df['Symbol'].str.replace('.', '-', regex=True).tolist()[:40]
    else:
        df = [t for t in tables if 'Ticker' in t.columns][0]
        return [f"{t}.PA" if not str(t).endswith(".PA") else t for t in df['Ticker']]

# --- RÉCUPÉRATION DES DONNÉES FONDAMENTALES ---
@st.cache_data(ttl=3600)
def fetch_fundamental_data(tickers):
    results = []
    session = get_session()
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, t in enumerate(tickers):
        try:
            status_text.text(f"Analyse de {t}...")
            stock = yf.Ticker(t, session=session)
            info = stock.info
            
            # Extraction sécurisée des données
            results.append({
                "Ticker": t,
                "Nom": info.get("longName", "N/A"),
                "Secteur": info.get("sector", "N/A"),
                "ROE (%)": info.get("returnOnEquity", 0) * 100,
                "PEG": info.get("trailingPegRatio", info.get("pegRatio", 0)),
                "Prix": info.get("currentPrice", 0)
            })
            # Petite pause pour ne pas saturer l'API
            time.sleep(0.2) 
        except Exception:
            continue
        progress_bar.progress((i + 1) / len(tickers))
    
    status_text.empty()
    progress_bar.empty()
    return pd.DataFrame(results)

# --- INTERFACE ---
st.title("🚀 Scanner de Qualité Financière")

with st.sidebar:
    index_choice = st.selectbox("Indice", ["CAC 40", "S&P 500"])
    min_roe = st.slider("ROE Minimum (%)", 0, 50, 15)
    max_peg = st.slider("PEG Maximum", 0.0, 3.0, 1.2)
    st.divider()
    if st.button("♻️ Forcer la mise à jour"):
        st.cache_data.clear()
        st.rerun()

# Logique principale
tickers = get_index_tickers(index_choice)
df = fetch_fundamental_data(tickers)

if not df.empty:
    # Filtrage sécurisé (on vérifie que les colonnes existent)
    if "ROE (%)" in df.columns and "PEG" in df.columns:
        mask = (df["ROE (%)"] >= min_roe) & (df["PEG"] <= max_peg) & (df["PEG"] > 0)
        filtered_df = df[mask]
        
        st.subheader(f"Résultats du screening ({len(filtered_df)} actions)")
        st.dataframe(filtered_df.sort_values("ROE (%)", ascending=False), use_container_width=True)
        
        # Bouton de téléchargement
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Télécharger en CSV", csv, "export_actions.csv", "text/csv")
    else:
        st.warning("Données incomplètes reçues de Yahoo.")
else:
    st.error("⚠️ Impossible de récupérer les données. Yahoo bloque peut-être l'accès.")
