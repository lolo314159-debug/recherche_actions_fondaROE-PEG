import streamlit as st
import yfinance as yf
import pandas as pd

# Configuration de la page
st.set_page_config(page_title="Scanner Financier Pro", layout="wide")

st.title("📊 Analyseur d'Actions : Qualité & Croissance")

# --- BARRE LATÉRALE : FILTRES ---
st.sidebar.header("Filtres de Recherche")

# Zone géographique (Exemple simplifié)
region = st.sidebar.selectbox("Zone Géographique", ["USA", "Europe", "Asie"])

# Sliders pour ROE et PEG
min_roe = st.sidebar.slider("ROE Minimum (%)", 0, 50, 15)
max_peg = st.sidebar.slider("PEG Maximum", 0.0, 5.0, 1.2)

# --- RECHERCHE SPÉCIFIQUE ---
st.sidebar.divider()
st.sidebar.subheader("Recherche par Ticker")
ticker_search = st.sidebar.text_input("Ex: AAPL, MSFT, LVMH.PA").upper()

# --- LOGIQUE DE RÉCUPÉRATION ---
def get_stock_data(ticker_list):
    data = []
    for t in ticker_list:
        try:
            stock = yf.Ticker(t)
            info = stock.info
            data.append({
                "Ticker": t,
                "Nom": info.get("longName"),
                "Secteur": info.get("sector"),
                "ROE (%)": info.get("returnOnEquity", 0) * 100,
                "PEG": info.get("trailingPegRatio", info.get("pegRatio", 0)),
                "Prix": info.get("currentPrice"),
                "Market Cap": info.get("marketCap")
            })
        except:
            continue
    return pd.DataFrame(data)

# --- AFFICHAGE ---
if ticker_search:
    st.subheader(f"Analyse de {ticker_search}")
    df_single = get_stock_data([ticker_search])
    if not df_single.empty:
        st.table(df_single)
    else:
        st.error("Ticker non trouvé.")

st.divider()

st.subheader(f"🔍 Résultats du Screen ({region})")
# Simulation d'une liste (Dans un vrai projet, on itérerait sur un index comme le S&P500)
tickers_demo = ["AAPL", "GOOGL", "MSFT", "TSLA", "META", "NVDA", "ASML", "MC.PA"]
df_screen = get_stock_data(tickers_demo)

# Application des filtres
filtered_df = df_screen[
    (df_screen["ROE (%)"] >= min_roe) & 
    (df_screen["PEG"] <= max_peg) & 
    (df_screen["PEG"] > 0)
]

if not filtered_df.empty:
    st.dataframe(filtered_df.sort_values("ROE (%)", ascending=False), use_container_width=True)
else:
    st.info("Aucune action ne correspond à ces critères actuellement.")
