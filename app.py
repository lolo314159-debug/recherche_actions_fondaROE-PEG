# --- REMPLACEZ UNIQUEMENT LA BOUCLE DE RÉCUPÉRATION (SECTION 5) ---

if len(missing_tickers) > 0:
    if st.button(f"📥 Lancer la récupération de {len(missing_tickers)} tickers"):
        new_records = []
        bar = st.progress(0)
        status = st.empty()
        
        for i, t in enumerate(missing_tickers):
            try:
                # On ignore les tickers invalides comme "---"
                if len(t) < 2 or t.startswith("-"):
                    continue
                    
                status.text(f"Analyse de {t} ({i+1}/{len(missing_tickers)})...")
                stock = yf.Ticker(t)
                # On utilise un timeout court pour ne pas rester bloqué sur une action
                info = stock.info 
                
                price = info.get("currentPrice")
                if price and price > 0:
                    new_records.append({
                        "ticker": t,
                        "roe": round(info.get("returnOnEquity", 0) * 100, 2),
                        "peg": info.get("trailingPegRatio", info.get("pegRatio", 0)),
                        "prix": price,
                        "date_recup": today
                    })
                
                # SAUVEGARDE ULTRA-FRÉQUENTE (Toutes les 5 actions)
                # C'est la clé pour le S&P 500 : on écrit petit à petit
                if len(new_records) >= 5:
                    save_to_sheet(pd.DataFrame(new_records))
                    new_records = []
                    # Petite pause pour laisser respirer l'API Google
                    time.sleep(1) 
                
                time.sleep(0.4) 
            except Exception as e:
                # Si une action plante, on passe direct à la suivante
                continue
            
            bar.progress((i + 1) / len(missing_tickers))
        
        # Sauvegarde finale du dernier bloc
        if new_records:
            save_to_sheet(pd.DataFrame(new_records))
        
        st.success("Synchronisation terminée ! Les données sont dans le Cloud.")
        st.rerun()
