import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Connexion sécurisée
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("Test de Connexion Sécurisée")

if st.button("Écrire une ligne de test"):
    test_df = pd.DataFrame([{
        "ticker": "TEST_OK",
        "date_recup": datetime.now().strftime('%Y-%m-%d %H:%M')
    }])
    
    # On lit l'existant pour ne pas l'écraser
    existing = conn.read(worksheet="stock_data")
    updated = pd.concat([existing, test_df], ignore_index=True)
    
    # Écriture
    conn.update(worksheet="stock_data", data=updated)
    st.success("Bravo ! Le script a réussi à écrire dans votre Google Sheet.")
