import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Test Final Connexion", layout="wide")

# Connexion via les Secrets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Erreur de configuration : {e}")

st.title("🛡️ Vérification de la Liaison Cloud")

if st.button("📝 Tester l'écriture immédiate"):
    try:
        # Création d'une ligne de test
        test_data = pd.DataFrame([{
            "ticker": "CONNEXION_OK",
            "date_recup": datetime.now().strftime('%Y-%m-%d %H:%M')
        }])
        
        # Tentative de lecture de l'existant
        df_existant = conn.read(worksheet="stock_data", ttl=0)
        
        # Fusion et Envoi
        df_final = pd.concat([df_existant, test_data], ignore_index=True)
        conn.update(worksheet="stock_data", data=df_final)
        
        st.success("✅ Incroyable ! Le fichier Google Sheet a été mis à jour avec succès.")
        st.dataframe(df_final)
    except Exception as e:
        st.error(f"L'écriture a échoué. Détails : {e}")
        st.info("Vérifiez que vous avez partagé le Sheet avec l'e-mail du compte de service !")
