import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import mplcursors
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from data_loader import load_data
from shared_data import shared_data


class SegmentationPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.data = load_data()
        self.sort_directions = {}

        if self.data is None or self.data.empty:
            messagebox.showerror("Erreur", "Aucune donnée disponible pour la segmentation.")
            return

        # 🔹 Reset pour export
        shared_data["segment_df"] = None
        shared_data["figs"] = []

        self.init_ui()

    def init_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        self.tab_table = ttk.Frame(self.notebook)
        self.tab_demo = ttk.Frame(self.notebook)
        self.tab_rfm = ttk.Frame(self.notebook)
        self.tab_produit = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_table, text="Tableau récapitulatif")
        self.notebook.add(self.tab_demo, text="Démographique")
        self.notebook.add(self.tab_rfm, text="RFM (K-Means)")
        self.notebook.add(self.tab_produit, text="Produit")

        # === Onglet tableau ===
        self.build_table_tab()

        # === Onglet démographique ===
        self.build_demo_graphs()

        # === Onglet RFM ===
        self.build_rfm_kmeans()

        # === Onglet produit ===
        self.build_produit_graphs()

    # ---------------------------------------------------------------------
    def build_table_tab(self):
        ttk.Label(
            self.tab_table,
            text="Segmentation – Tableau récapitulatif",
            font=("Segoe UI", 14, "bold")
        ).pack(pady=10, anchor="w")

        columns = ["client_id", "âge", "sexe", "ville", "catégorie", "montant_total"]
        df = self.data[columns].copy()

        # ✅ On stocke pour export
        shared_data["segment_df"] = df.copy()

        frame_container = ttk.Frame(self.tab_table)
        frame_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(frame_container, columns=columns, show="headings")
        self.tree.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(frame_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")

        for col in columns:
            self.sort_directions[col] = False
            self.tree.heading(col, text=col.capitalize(), command=lambda c=col: self.sort_column(c))
            font = tkFont.Font()
            max_width = font.measure(col.title())
            self.tree.column(col, anchor="center", width=max_width + 80)

        self.display_table(df)

    def sort_column(self, col):
        reverse = self.sort_directions[col]
        try:
            sorted_df = shared_data["segment_df"].sort_values(by=col, ascending=not reverse)
        except Exception as e:
            messagebox.showerror("Erreur de tri", str(e))
            return
        self.sort_directions[col] = not reverse
        self.display_table(sorted_df)
        shared_data["segment_df"] = sorted_df.reset_index(drop=True)

    def display_table(self, df):
        self.tree.delete(*self.tree.get_children())
        for _, row in df.iterrows():
            values = [row[col] for col in self.tree["columns"]]
            self.tree.insert("", tk.END, values=values)

    # ---------------------------------------------------------------------
    def build_demo_graphs(self):
        frame = ttk.Frame(self.tab_demo)
        frame.pack(fill="both", expand=True)

        fig, axs = plt.subplots(1, 3, figsize=(15, 5))

        # Répartition par sexe
        sexe_counts = self.data["sexe"].value_counts()
        wedges, _, _ = axs[0].pie(
            sexe_counts,
            labels=sexe_counts.index,
            autopct="%1.1f%%",
            startangle=90
        )
        axs[0].set_title("Répartition par sexe")
        mplcursors.cursor(wedges, hover=True)

        # Répartition par âge
        if "âge" in self.data.columns:
            self.data["tranche_age"] = pd.cut(
                self.data["âge"],
                bins=[0, 18, 30, 45, 60, 100],
                labels=["-18", "18-30", "30-45", "45-60", "60+"]
            )
            age_counts = self.data["tranche_age"].value_counts().sort_index()
            bars = axs[1].bar(age_counts.index.astype(str), age_counts.values, color="skyblue")
            axs[1].set_title("Répartition par âge")
            axs[1].set_ylabel("Clients")
            mplcursors.cursor(bars, hover=True)

        # Répartition par ville
        ville_counts = self.data["ville"].value_counts().head(10)
        bars2 = axs[2].barh(ville_counts.index[::-1], ville_counts.values[::-1], color="lightgreen")
        axs[2].set_title("Top 10 villes")
        mplcursors.cursor(bars2, hover=True)

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        shared_data["figs"].append(fig)   # ✅ sauvegarde graphique

    # ---------------------------------------------------------------------
    def build_rfm_kmeans(self):
        frame = ttk.Frame(self.tab_rfm)
        frame.pack(fill="both", expand=True)

        if not {"date_achat", "montant_total", "achat_id"}.issubset(self.data.columns):
            ttk.Label(frame, text="Colonnes nécessaires pour RFM manquantes.").pack()
            return

        self.data["date_achat"] = pd.to_datetime(self.data["date_achat"], errors="coerce")
        snapshot_date = self.data["date_achat"].max() + pd.Timedelta(days=1)

        rfm = self.data.groupby("client_id").agg({
            "date_achat": lambda x: (snapshot_date - x.max()).days,
            "achat_id": "count",
            "montant_total": "sum"
        }).rename(columns={"date_achat": "Recence", "achat_id": "Frequence", "montant_total": "Montant"})

        scaler = StandardScaler()
        rfm_scaled = scaler.fit_transform(rfm)

        kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
        rfm["Cluster"] = kmeans.fit_predict(rfm_scaled)

        # ✅ On met à jour segment_df au lieu de créer une clé différente
        shared_data["segment_df"] = rfm.copy()

        fig, ax = plt.subplots(figsize=(7, 5))
        scatter = ax.scatter(rfm["Recence"], rfm["Frequence"], c=rfm["Cluster"], cmap="tab10", alpha=0.7)
        ax.set_title("Segmentation RFM – KMeans")
        ax.set_xlabel("Récence (jours)")
        ax.set_ylabel("Fréquence")
        legend1 = ax.legend(*scatter.legend_elements(), title="Clusters")
        ax.add_artist(legend1)
        mplcursors.cursor(scatter, hover=True)

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        shared_data["figs"].append(fig)

    # ---------------------------------------------------------------------
    def build_produit_graphs(self):
        frame = ttk.Frame(self.tab_produit)
        frame.pack(fill="both", expand=True)

        if "catégorie" not in self.data.columns:
            ttk.Label(frame, text="Colonne 'catégorie' manquante.").pack()
            return

        fig, axs = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle("Segmentation Produits")

        # === Top 10 catégories ===
        cat_sums = (
            self.data.groupby("catégorie")["montant_total"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )
        bars1 = axs[0].barh(cat_sums.index[::-1], cat_sums.values[::-1], color="skyblue")
        axs[0].set_title("Top 10 Catégories par montant")
        axs[0].set_xlabel("Montant total (FCFA)")
        axs[0].tick_params(axis="y", labelsize=9)
        cursor1 = mplcursors.cursor(bars1, hover=True)

        @cursor1.connect("add")
        def on_hover1(sel):
            cat = cat_sums.index[::-1][sel.index]
            val = cat_sums.values[::-1][sel.index]
            sel.annotation.set_text(f"{cat}\n{val:,.0f} FCFA")

        # === Top 10 produits ===
        if "produit" in self.data.columns:
            prod_sums = (
                self.data.groupby("produit")["montant_total"]
                .sum()
                .sort_values(ascending=False)
                .head(10)
            )
            bars2 = axs[1].barh(prod_sums.index[::-1], prod_sums.values[::-1], color="orange")
            axs[1].set_title("Top 10 Produits par montant")
            axs[1].set_xlabel("Montant total (FCFA)")
            axs[1].tick_params(axis="y", labelsize=9)
            cursor2 = mplcursors.cursor(bars2, hover=True)

            @cursor2.connect("add")
            def on_hover2(sel):
                prod = prod_sums.index[::-1][sel.index]
                val = prod_sums.values[::-1][sel.index]
                sel.annotation.set_text(f"{prod}\n{val:,.0f} FCFA")

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        shared_data["figs"].append(fig)
