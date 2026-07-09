# Dictionnaire global pour partager les données entre onglets
shared_data = {
    "df": None,                # Contiendra le DataFrame principal
    "rfm_results": None,
    "segment_df": None,
    "forecasts": None,         # Résultats de prévisions
    "predictions": None,       # Résultats de prédictions
    "anomalies": None,         # Résultats de détection d'anomalies
    "simulation_results": None,# Résultats des simulations
    "churn_risk": None,        # Risque de désabonnement
    
    "last_update": None,       # Date ou heure de la dernière mise à jour
    "OverviewPage": None,
    
    "filters": None,           # Filtres appliqués
    
    
    
    "export_data": None,       # Données à exporter
    "ai_responses": None,      # Résultats des interactions IA

    "summary": {},
                                # Résumés et statistiques diverses
    # Nouveau pour stocker tous les graphiques
    "figs": []
}
