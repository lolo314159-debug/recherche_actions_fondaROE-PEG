import streamlit as st
import pandas as pd
import yfinance as yf
import requests

st.set_page_config(page_title="Guide des Actions & Tickers", layout="wide")

# --- RÉCUPÉRATION DES LISTES OFFICIELLES ---
@st.cache_data(ttl=86400)
def get_index_data(index_name):
    header = {"User-Agent": "Mozilla/5.0"}
    try:
        if index_name == "S&P 500 (USA)":
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            res = requests.get(url, headers=header)
            df = pd.read_html(res.text)[0]
            # Nettoyage pour Yahoo Finance
            df['Ticker_Yahoo'] = df['Symbol'].str.replace('.', '-', regex=True)
            return df[['Security', 'Ticker_Yahoo', 'GICS Sector']]
        
        elif index_name == "CAC 40 (France)":
            url = "https://en.wikipedia.org/wiki/CAC_40"
            res = requests.get(url, headers=header)
            tables = pd.read_html(res.text)
            df = [t for t in tables if 'Ticker' in t.columns][0]
            # Ajout du suffixe .PA pour Paris
            df['Ticker_Yahoo'] = df['Ticker'].apply(lambda x: f"{x}.PA" if not str(x).endswith(".PA") else x)
            return df[['Company', 'Ticker_Yahoo', 'Sector']]
    except Exception as e:
        st.error(f"Erreur lors de la lecture de la liste : {e}")
        return pd.DataFrame()

# --- INTERFACE ---
st.title("📊 Liste des Actions et Analyse Fondamentale")

index_choice = st.sidebar.selectbox("Choisissez un Indice", ["CAC 40 (France)", "S&P 500 (USA)"])

# Chargement de la liste
df_list = get_index_data(index_choice)

if not df_list.empty:
    st.subheader(f"Actions disponibles dans le {index_choice}")
    
    # Barre de recherche pour trouver une entreprise par son nom
    search_name = st.text_input("🔍 Chercher une entreprise par son nom (ex: LVMH, Apple, Total...)").lower()
    
    if search_name:
        # Recherche flexible sur le nom ou le ticker
        name_col = 'Company' if 'Company' in df_list.columns else 'Security'
        df_display = df_list[df_list[name_col].str.lower().contains(search_name) | df_list['Ticker_Yahoo'].str.lower().contains(search_name)]
    else:
        df_display = df_list

    st.dataframe(df_display, use_container_width=True)

    # --- ANALYSE DÉTAILLÉE ---
    st.divider()
    st.subheader("🧐 Analyse d'une action spécifique")
    
    # Liste de sélection basée sur le nom pour l'utilisateur
    name_col = 'Company' if 'Company' in df_list.columns else 'Security'
    options = df_list[name_col].tolist()
    selected_company = st.selectbox("Sélectionnez l'entreprise à analyser :", options)

    if selected_company:
        # Trouver le ticker correspondant
        ticker = df_list[df_list[name_col] == selected_company]['Ticker_Yahoo'].values[0]
        
        with st.spinner(f"Récupération des données pour {ticker}..."):
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                col1, col2, col3 = st.columns(3)
                col1.metric("ROE (%)", f"{info.get('returnOnEquity', 0) * 100:.2f} %")
                col2.metric("PEG Ratio", info.get('trailingPegRatio', info.get('pegRatio', 'N/A')))
                col3.metric("Prix Actuel", f"{info.get('currentPrice', 'N/A')} {info.get('currency', '')}")
                
                with st.expander("Voir tous les détails financiers"):
                    st.json({
                        "Secteur": info.get("sector"),
                        "Industrie": info.get("industry"),
                        "Résumé": info.get("longBusinessSummary")
                    })
            except:
                st.error("Désolé, Yahoo
