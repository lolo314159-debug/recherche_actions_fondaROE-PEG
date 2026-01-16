import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time

st.set_page_config(page_title="Scanner de Qualité Pro", layout="wide")

# --- CONFIGURATION SESSION ---
def get_session():
    session = requests.Session()
    # On utilise un User-Agent très récent pour paraître "humain"
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    return session

# --- RÉCUPÉRATION DES TICKERS ---
@st.cache_data(ttl=86400)
def get_index_tickers(index_name):
    session = get_session()
    try:
        if index_name == "S&P 500":
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            res = session.get(url, timeout=10)
            df = pd.read_html(res.text)[0]
            # On limite à 50 pour le S&P 500 pour éviter le blocage IP sur Streamlit Cloud
            return df['Symbol'].str.replace('.', '-', regex=True).tolist()[:50]
        else:
            url = "https://en.wikipedia.org/wiki/CAC_40"
            res = session.get(url, timeout=10)
            tables = pd.read_html(res.text)
            df = [t for t in tables if 'Ticker' in t.columns][0]
            return [f"{t}.PA" if not str(t).endswith(".PA") else t for t in df['Ticker']]
    except Exception as e:
        st.error(f"Erreur Wikipedia: {e}")
        return []

# --- RÉCUPÉRATION DES DONNÉES FONDAMENTALES ---
@st.cache_data(ttl=3600)
def fetch_fundamental_data(tickers):
    results = []
    session = get_session()
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, t in enumerate(tickers):
        try:
            status_text.text(f"Analyse de {t} ({i+1}/{len(tickers)})...")
            stock = yf.Ticker(t, session=session)
            info = stock.info
            
            # On ne garde que si les données essentielles existent
            results.append({
                "Ticker": t,
                "Nom": info.get("longName", "N/A"),
                "Secteur": info.get("sector", "N/A"),
                "ROE (%)": info.get("returnOnEquity", 0) * 100,
                "PEG": info.get("trailingPegRatio", info.get("pegRatio", 0)),
                "Prix": info.get("currentPrice", 0)
            })
            # PAUSE CRITIQUE : évite de se faire bannir par Yahoo
            time.sleep(0.5) 
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
    if st.button("♻️ Réinitialiser et Forcer la mise à jour"):
        st.cache_data.clear()
        st.rerun()

# Logique principale
tickers = get_index_tickers(index_choice)

if tickers:
    df = fetch_fundamental_data(tickers)
    
    if not df.empty:
        # Filtrage sécurisé
        mask = (df["ROE (%)"] >= min_roe) & (df["PEG"] <= max_peg) & (df["PEG"] > 0)
        filtered_df = df[mask]
        
        st.subheader(f"Résultats du screening ({len(filtered_df)} actions trouvées)")
        st.dataframe(filtered_df.sort_values("ROE (%)", ascending=False), use_container_width=True)
        
        # Bouton de téléchargement
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Télécharger les résultats (CSV)", csv, "screening.csv", "text/csv")
    else:
        st.warning("⚠️ Yahoo Finance bloque l'accès. Attendez 5 min ou changez d'indice.")
else:
    st.error("Impossible de récupérer la liste des tickers.")
