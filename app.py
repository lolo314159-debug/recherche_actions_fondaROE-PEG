# --- FILTRES AVANCÉS ---
st.sidebar.header("🎯 Critères de Sélection")

# Filtre ROE (Qualité)
min_roe = st.sidebar.slider("ROE Minimum (%)", 0, 50, 15, help="Rentabilité des capitaux propres. On cherche souvent > 15%.")

# Filtre PEG (Valorisation)
max_peg = st.sidebar.slider("PEG Maximum", 0.0, 5.0, 1.2, step=0.1, help="PEG < 1 indique souvent une action sous-évaluée par rapport à sa croissance.")

# Filtrage du DataFrame
if not stored_df.empty:
    # Conversion en numérique pour éviter les erreurs de comparaison
    stored_df['roe'] = pd.to_numeric(stored_df['roe'], errors='coerce')
    stored_df['peg'] = pd.to_numeric(stored_df['peg'], errors='coerce')

    # Application des filtres
    mask = (stored_df['ticker'].isin(wiki_tickers)) & \
           (stored_df['date_recup'] == today) & \
           (stored_df['roe'] >= min_roe) & \
           (stored_df['peg'] <= max_peg) & \
           (stored_df['peg'] > 0) # On exclut les PEG à 0 (données manquantes)

    filtered_df = stored_df[mask].sort_values("roe", ascending=False)

    # Affichage des résultats filtrés
    st.subheader(f"✨ Pépites détectées ({len(filtered_df)})")
    
    if not filtered_df.empty:
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        
        # Petit résumé visuel
        st.caption(f"Filtré pour ROE ≥ {min_roe}% et PEG ≤ {max_peg}")
    else:
        st.warning("Aucune action ne correspond à ces critères aujourd'hui. Essayez d'assouplir les filtres.")
