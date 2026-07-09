import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import mplcursors
from sklearn.ensemble import IsolationForest
import numpy as np

from data_loader import load_data
from shared_data import shared_data


class AnomaliesPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        # Charger données
        self.df = load_data()
        if self.df is None or self.df.empty:
            ttk.Label(self, text="Aucune donnée disponible.", font=("Segoe UI", 14)).pack(pady=20)
            return

        self.df["montant_total"] = pd.to_numeric(
            self.df.get("montant_total", 0), errors="coerce"
        ).fillna(0)

        # Détection des anomalies
        self.detect_anomalies()

        # Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        # Onglets
        self.table_frame = ttk.Frame(self.notebook)
        self.graph_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.table_frame, text="Tableau anomalies")
        self.notebook.add(self.graph_frame, text="Graphiques")

        # Table + filtres
        self.create_filter_controls()
        self.create_table()

        # Graphiques
        self.create_graphs()

    # ------------------------------------------------------------------
    def detect_anomalies(self):
        anomalies_list = []

        # IQR
        Q1 = self.df["montant_total"].quantile(0.25)
        Q3 = self.df["montant_total"].quantile(0.75)
        IQR = Q3 - Q1
        lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
        outliers_iqr = self.df[
            (self.df["montant_total"] < lower) | (self.df["montant_total"] > upper)
        ].copy()
        outliers_iqr["type_anomalie"] = "IQR"
        anomalies_list.append(outliers_iqr)

        # Z-score
        mean, std = self.df["montant_total"].mean(), self.df["montant_total"].std()
        z_scores = (self.df["montant_total"] - mean) / std
        outliers_z = self.df[(np.abs(z_scores) > 3)].copy()
        outliers_z["type_anomalie"] = "Z-score"
        anomalies_list.append(outliers_z)

        # Isolation Forest
        iso = IsolationForest(contamination=0.05, random_state=42)
        preds = iso.fit_predict(self.df[["montant_total"]])
        outliers_if = self.df[preds == -1].copy()
        outliers_if["type_anomalie"] = "IsolationForest"
        anomalies_list.append(outliers_if)

        # Fusion
        self.anomalies = pd.concat(anomalies_list).drop_duplicates()
        shared_data["anomalies"] = self.anomalies.copy()

    # ------------------------------------------------------------------
    # Tableau
    def create_filter_controls(self):
        control_frame = ttk.Frame(self.table_frame)
        control_frame.pack(fill="x", pady=5)

        ttk.Label(
            control_frame, text="Filtrer par type :", font=("Segoe UI", 10, "bold")
        ).pack(side="left", padx=5)

        self.filter_var = tk.StringVar()
        self.filter_combo = ttk.Combobox(
            control_frame,
            textvariable=self.filter_var,
            values=["Tous", "IQR", "Z-score", "IsolationForest"],
            state="readonly",
        )
        self.filter_combo.current(0)
        self.filter_combo.pack(side="left", padx=5)
        self.filter_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_table())

    def create_table(self):
        cols = ["client_id", "achat_id", "montant_total", "type_anomalie"]
        self.tree = ttk.Treeview(self.table_frame, columns=cols, show="headings")
        self.tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        vsb = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")

        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=120)

        self.refresh_table()

        # Sélection ligne → popup détail
        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        selected = self.filter_var.get()
        if selected == "Tous":
            df_filtered = self.anomalies
        else:
            df_filtered = self.anomalies[
                self.anomalies["type_anomalie"] == selected
            ]

        for _, row in df_filtered.iterrows():
            self.tree.insert(
                "",
                "end",
                values=[
                    row.get("client_id", ""),
                    row.get("achat_id", ""),
                    row.get("montant_total", ""),
                    row.get("type_anomalie", ""),
                ],
            )

    # ------------------------------------------------------------------
    # Popup détail client
    def _on_row_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        client_id = item["values"][0]
        self._open_client_detail(client_id)

    def _open_client_detail(self, client_id):
        df_client = self.df[self.df["client_id"] == client_id]
        if df_client.empty:
            messagebox.showinfo("Détails client", f"Aucune donnée pour le client {client_id}")
            return

        top = tk.Toplevel(self)
        top.title(f"Détails client {client_id}")
        top.geometry("700x400")

        recap = f"Client {client_id}\n" \
                f"Nombre d’achats : {len(df_client)}\n" \
                f"Montant cumulé : {df_client['montant_total'].sum():,.0f} FCFA"
        ttk.Label(top, text=recap, justify="left").pack(anchor="w", padx=10, pady=10)

        cols = list(df_client.columns)
        tree = ttk.Treeview(top, columns=cols, show="headings")
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=120, anchor="center")
        tree.pack(fill="both", expand=True, padx=8, pady=8)

        for _, r in df_client.iterrows():
            tree.insert("", "end", values=[r[c] for c in cols])

    # ------------------------------------------------------------------
    # Graphiques adaptés
    def create_graphs(self):
        # Nettoyer
        for widget in self.graph_frame.winfo_children():
            widget.destroy()

        figs = []

        # ---- Résumé global ----
        counts = self.anomalies["type_anomalie"].value_counts()
        summary = " | ".join([f"{k}: {v}" for k, v in counts.items()])
        ttk.Label(self.graph_frame, text=f"Résumé anomalies → {summary}",
                  font=("Segoe UI", 12, "bold"), foreground="red").pack(pady=10)

        # ---- Graph 1 : Bar chart comparatif ----
        fig1, ax1 = plt.subplots(figsize=(6, 4))
        bars = ax1.bar(counts.index, counts.values, color=["orange", "green", "red"])
        ax1.set_title("Nombre d'anomalies par méthode")
        ax1.set_ylabel("Clients")
        cursor1 = mplcursors.cursor(bars, hover=True)
        @cursor1.connect("add")
        def on_add(sel):
            sel.annotation.set_text(f"{counts.index[sel.index]}: {counts.values[sel.index]}")
        figs.append(fig1)

        # ---- Graph 2 : Scatter normal vs anomalies ----
        fig2, ax2 = plt.subplots(figsize=(7, 4))
        normal = self.df[~self.df.index.isin(self.anomalies.index)]
        ax2.scatter(normal.index, normal["montant_total"], color="lightgrey", s=10, label="Normaux")

        for method, color in [("IQR", "orange"), ("Z-score", "green"), ("IsolationForest", "red")]:
            subset = self.anomalies[self.anomalies["type_anomalie"] == method]
            sc = ax2.scatter(subset.index, subset["montant_total"], s=40, color=color, label=method, alpha=0.8)
            cursor = mplcursors.cursor(sc, hover=True)
            @cursor.connect("add")
            def on_add(sel, m=method, sub=subset):
                row = sub.iloc[sel.index]
                sel.annotation.set_text(
                    f"Client {row['client_id']}\nMéthode: {m}\nMontant={row['montant_total']:,.0f} FCFA"
                )

        ax2.set_title("Anomalies détectées par méthode")
        ax2.set_xlabel("Index client")
        ax2.set_ylabel("Montant total")
        ax2.legend()
        figs.append(fig2)

        # ---- Graph 3 : Histogramme avec anomalies ----
        fig3, ax3 = plt.subplots(figsize=(7, 4))
        counts_all, bins, patches = ax3.hist(
            self.df["montant_total"], bins=30, color="skyblue", edgecolor="black", alpha=0.6, label="Normaux"
        )
        ax3.hist(self.anomalies["montant_total"], bins=bins, color="red", edgecolor="black", alpha=0.7, label="Anomalies")

        ax3.set_title("Distribution des montants avec anomalies")
        ax3.set_xlabel("Montant")
        ax3.set_ylabel("Clients")
        ax3.legend()

        cursor3 = mplcursors.cursor(ax3.patches, hover=True)
        @cursor3.connect("add")
        def on_add(sel):
            sel.annotation.set_text(f"{int(sel.artist.get_height())} clients")
        figs.append(fig3)

        # ---- Intégration Tkinter ----
        for fig in figs:
            canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, pady=10)

        # ---- Sauvegarde pour export ----
        shared_data["figs"] = figs
        shared_data["anomalies"] = self.anomalies.copy()
