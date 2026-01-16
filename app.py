def save_to_sheet(new_data):
    try:
        # Nettoyage avant sauvegarde : on supprime les lignes où le prix ou le ROE est à 0
        new_data = new_data[new_data['prix'] > 0] 
        
        if new_data.empty:
            return True

        existing = get_sheet_data()
        updated = pd.concat([existing, new_data], ignore_index=True)
        updated = updated.drop_duplicates(subset=['ticker', 'date_recup'], keep='last')
        
        # On s'assure que le fichier reste "propre" (pas de lignes vides)
        updated = updated.dropna(subset=['ticker'])
        
        conn.update(worksheet="stock_data", data=updated)
        return True
    except Exception as e:
        if "200" in str(e): return True 
        st.error(f"Erreur d'écriture : {e}")
        return False

# --- DANS LA BOUCLE DE RÉCUPÉRATION ---
# Modifiez la partie info.get pour être plus exigeant :
for i, t in enumerate(missing_tickers):
    try:
        status.text(f"Analyse de {t}...")
        stock = yf.Ticker(t)
        info = stock.info
        
        # On ne récupère que si le prix existe (évite les lignes vides)
        current_price = info.get("currentPrice")
        if current_price:
            new_records.append({
                "ticker": t,
                "roe": round(info.get("returnOnEquity", 0) * 100, 2),
                "peg": info.get("trailingPegRatio", info.get("pegRatio", 0)),
                "prix": current_price,
                "date_recup": today
            })
            time.sleep(0.6) # Un peu plus de temps pour le S&P 500 (500 requêtes !)
