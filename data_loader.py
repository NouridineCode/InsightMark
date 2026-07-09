import pandas as pd

def load_data():
    # Charger le fichier CSV corrigé
    df = pd.read_csv("data/dataset_clients_et_prospects.csv")

    # Nettoyage de base
    df.columns = df.columns.str.strip()  # Supprimer les espaces dans les noms de colonnes

    # Conversion des types
    df["client_id"] = df["client_id"].astype(str)
    df["achat_id"] = df["achat_id"].astype(str)
    df["montant_total"] = pd.to_numeric(df["montant_total"], errors="coerce").fillna(0)

    # Convertir date_achat sans supprimer les NaT
    if "date_achat" in df.columns:
        df["date_achat"] = pd.to_datetime(df["date_achat"], errors="coerce")

    # Colonnes manquantes par défaut (utile si tu ajoutes des fonctionnalités plus tard)
    for col in ["segment", "produit", "categorie_produit", "ville"]:
        if col not in df.columns:
            df[col] = "Inconnu"

    # Colonnes binaires déjà nettoyées (achat_effectue, retour)
    if "achat_effectue" in df.columns:
        df["achat_effectue"] = df["achat_effectue"].astype(int)
    if "retour" in df.columns:
        df["retour"] = df["retour"].astype(int)

    return df
