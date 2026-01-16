import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
import time

# Configuration de la page
st.set_page_config(page_title="Screener Intelligent & Archive Cloud", layout="wide")

# --- CONNEXION GOOGLE SHEETS ---
# Utilise la configuration définie dans les Secrets Streamlit
conn = st.connection("gsheets", type=GSheetsConnection)

def get_sheet_data(worksheet):
    """Lit les données depuis Google Sheets sans cache pour avoir le temps réel"""
    try:
        return conn.read(worksheet=worksheet, ttl=0)
    except Exception:
        # Retourne un DataFrame vide avec les bonnes colonnes si la feuille est neuve
        return pd.DataFrame(columns=['ticker', 'roe', 'peg', 'prix', 'date_recup'])

def save_to_sheet(new_data, worksheet):
    """Fusionne les nouvelles données avec l'existant et sauvegarde"""
    try:
        existing_data = get_sheet_data(worksheet)
        # Fusion et suppression des doublons (on garde la version la plus récente)
        updated_data = pd.concat([existing_data, new_data], ignore_index=True)
        updated_data = updated_data.drop_duplicates(subset=['ticker', 'date_recup'], keep='last')
        
        # Envoi vers Google Sheets
        conn.update(worksheet=worksheet, data=updated_data)
        return True
    except Exception as e:
        st.error(f"Erreur d'écriture Google Sheets : {e}")
        return False

# --- RÉCUPÉRATION DES TICKERS (WIKIPEDIA) ---
@st.cache_data(ttl=86400)
def get_wiki_tickers(index_name):
    header = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        if index_name == "S&P 500":
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            res = requests.get(url, headers=header)
            df = pd.read_html(res.text)[0]
            return df['Symbol'].str.replace('.', '-', regex=True).tolist()
        else:
            url = "https://en.wikipedia.org/wiki/CAC_40"
            res = requests.get(url, headers=header)
            df = [t for t in pd.read_html(res.text) if 'Ticker' in t.columns][0]
            return [f"{t}.PA" if not str(t).endswith(".PA") else t for t in df['Ticker']]
    except Exception as e:
        st.error(f"Erreur Wikipedia : {e}")
        return []

# --- INTERFACE PRINCIPALE ---
st.title("🛡️ Screener Intelligent & Archive Cloud")

# Sidebar pour les réglages
index_choice = st.sidebar.selectbox("Choisir l'indice", ["CAC 40", "S&P 500"])
roe_min = st.sidebar.slider("ROE Minimum (%)", 0, 50, 15)
today = datetime.now().strftime('%Y-%m-%d')

# Diagnostic de connexion
if st.sidebar.button("🛠️ Tester la connexion au Sheet"):
    test_df = pd.DataFrame([{"ticker": "TEST", "roe": 0, "peg": 0, "prix": 0, "date_recup": today}])
    if save_to_sheet(test_df, "stock_data"):
        st.sidebar.success("Connexion OK ! Vérifiez votre Google Sheet.")
    else:
        st.sidebar.error("Échec d'écriture. Vérifiez l'URL et le partage 'Éditeur'.")

# --- LOGIQUE DE SYNCHRONISATION ---

with st.spinner("Analyse de la base de données..."):
    # 1. Liste officielle Wikipedia
    wiki_tickers = get_wiki_tickers(index_choice)
    
    # 2. Données déjà présentes en base pour aujourd'hui
    stored_df = get_sheet_data("stock_data")
    if not stored_df.empty and 'date_recup' in stored_df.columns:
        synced_today = stored_df[stored_df['date_recup'] == today]['ticker'].tolist()
    else:
        synced_today = []

    # 3. Calcul des manquants
    missing_tickers = [t for t in wiki_tickers if t not in synced_today]

# Affichage des compteurs
c1, c2, c3 = st.columns(3)
c1.metric("Total Indice", len(wiki_tickers))
c2.metric("Déjà en Base (Aujourd'hui)", len(synced_today))
c3.metric("Manquants", len(missing_tickers))

# Bouton de récupération
if len(missing_tickers) > 0:
    if st.button(f"📥 Récupérer les {len(missing_tickers)} manquants sur Yahoo Finance"):
        new_records = []
        prog_bar = st.progress(0)
        status = st.empty()
        
        for i, t in enumerate(missing_tickers):
            try:
                status.text(f"Récupération de {t}...")
                stock = yf.Ticker(t)
                info = stock.info
                new_records.append({
                    "ticker": t,
                    "roe": round(info.get("returnOnEquity", 0) * 100, 2),
                    "peg": info.get("trailingPegRatio", info.get("pegRatio", 0)),
                    "prix": info.get("currentPrice", 0),
                    "date_recup": today
                })
                # Pause pour éviter le bannissement Yahoo
                time.sleep(0.5) 
                
                # Sauvegarde par blocs de 5 pour ne pas tout perdre en cas de crash
                if len(new_records) >= 5:
                    save_to_sheet(pd.DataFrame(new_records), "stock_data")
                    new_records = []
                    
            except Exception:
                continue
            prog_bar.progress((i + 1) / len(missing_tickers))
        
        # Sauvegarde finale du reliquat
        if new_records:
            save_to_sheet(pd.DataFrame(new_records), "stock_data")
        
        status.empty()
        st.success("Mise à jour terminée !")
        st.rerun()

# --- AFFICHAGE DES RÉSULTATS ---
st.divider()
if not stored_df.empty:
    # On filtre pour n'afficher que les actions de l'indice choisi scannées AUJOURD'HUI
    mask = (stored_df['ticker'].isin(wiki_tickers)) & \
           (stored_df['date_recup'] == today) & \
           (pd.to_numeric(stored_df['roe'], errors='coerce') >= roe_min)
    
    final_df = stored_df[mask].sort_values("roe", ascending=False)
    
    st.subheader(f"Résultats filtrés : {index_choice} (ROE > {roe_min}%)")
    st.dataframe(final_df, use_container_width=True, hide_index=True)
else:
    st.info("La base de données est vide. Cliquez sur le bouton de récupération pour commencer.")
