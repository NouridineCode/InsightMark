import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import mplcursors
import matplotlib.ticker as mticker
from data_loader import load_data
from shared_data import shared_data


# ========= Fonction utilitaire pour créer une carte KPI compacte =========
def create_kpi_card(parent, title, value, bg_color="#2c2c3c", hover_color="#3d3d5c"):
    frame = tk.Frame(parent, bg=bg_color, bd=0, relief="flat", width=160, height=80)
    frame.pack_propagate(False)

    label_title = tk.Label(frame, text=title, font=("Segoe UI", 10, "bold"),
                           fg="white", bg=bg_color)
    label_title.pack(pady=(5, 0))

    label_value = tk.Label(frame, text=value, font=("Segoe UI", 12, "bold"),
                           fg="#00cec9", bg=bg_color)
    label_value.pack(pady=(0, 5))

    # Effet hover
    def on_enter(e):
        frame.config(bg=hover_color)
        label_title.config(bg=hover_color)
        label_value.config(bg=hover_color)

    def on_leave(e):
        frame.config(bg=bg_color)
        label_title.config(bg=bg_color)
        label_value.config(bg=bg_color)

    frame.bind("<Enter>", on_enter)
    frame.bind("<Leave>", on_leave)
    label_title.bind("<Enter>", on_enter)
    label_title.bind("<Leave>", on_leave)
    label_value.bind("<Enter>", on_enter)
    label_value.bind("<Leave>", on_leave)

    return frame


# ===================== Classe principale Overview =====================
class OverviewPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.data = load_data()
        shared_data["df"] = self.data

        # Initialisation pour export
        shared_data["last_fig"] = None
        shared_data["figs"] = []

        self.init_ui()

    def store_last_fig(self, fig):
        """Stocke le dernier graphique affiché + ajoute à la liste des figs"""
        shared_data["last_fig"] = fig
        if "figs" not in shared_data:
            shared_data["figs"] = []
        shared_data["figs"].append(fig)

    def init_ui(self):
        # Grille principale
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)  # Titre
        self.rowconfigure(1, weight=0)  # KPIs
        self.rowconfigure(2, weight=1)  # Graphiques

        # ======= Titre =======
        title = ttk.Label(
            self,
            text="📊 Tableau de Bord",
            font=("Segoe UI", 18, "bold"),
            foreground="#2c3e50"
        )
        title.grid(row=0, column=0, pady=20)

        # ======= KPIs =======
        kpi_frame = ttk.Frame(self)
        kpi_frame.grid(row=1, column=0, pady=15, sticky="ew")
        kpi_frame.columnconfigure((0, 1, 2, 3), weight=1)

        total_achats = len(self.data)
        total_revenus = self.data['montant_total'].sum()
        clients_actifs = self.data.groupby("client_id")["montant_total"].sum()
        total_clients = (clients_actifs > 0).sum()
        total_prospects = (clients_actifs == 0).sum()

        kpis = [
            ("👥 Clients", total_clients),
            ("🛒 Achats", total_achats),
            ("💰 Revenus", f"{total_revenus:,.0f} FCFA"),
            ("🎯 Prospects", total_prospects),
        ]

        for i, (label, value) in enumerate(kpis):
            card = create_kpi_card(kpi_frame, label, value)
            card.grid(row=0, column=i, padx=10, sticky="nsew")

        # ======= Grille des graphiques (2 lignes × 3 colonnes) =======
        graph_frame = ttk.Frame(self)
        graph_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)

        for i in range(2):
            graph_frame.rowconfigure(i, weight=1, uniform="row")
        for j in range(3):
            graph_frame.columnconfigure(j, weight=1, uniform="col")

        fig_size = (4.5, 3.5)

        # --- 1. Répartition par segment ---
        fig1, ax1 = plt.subplots(figsize=fig_size)
        seg_counts = self.data['segment'].value_counts()
        wedges, _, autotexts = ax1.pie(
            seg_counts.values, autopct="%1.1f%%", startangle=90,
            colors=sns.color_palette("Set2")
        )
        ax1.set_title("Répartition par segment", fontsize=11)
        for autotext in autotexts: autotext.set_fontsize(7)
        ax1.legend(wedges, seg_counts.index, title="Segments",
                   loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize=7)
        mplcursors.cursor(wedges, hover=True)
        FigureCanvasTkAgg(fig1, master=graph_frame).get_tk_widget().grid(row=0, column=0, padx=8, pady=8, sticky="nsew")
        self.store_last_fig(fig1)

        # --- 2. Répartition par ville ---
        fig2, ax2 = plt.subplots(figsize=fig_size)
        ville_counts = self.data['ville'].value_counts().nlargest(6)
        wedges, _, autotexts = ax2.pie(
            ville_counts.values, autopct="%1.1f%%", startangle=90,
            colors=sns.color_palette("pastel")
        )
        ax2.set_title("Répartition par ville", fontsize=11)
        for autotext in autotexts: autotext.set_fontsize(7)
        ax2.legend(wedges, ville_counts.index, title="Villes",
                   loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize=7)
        mplcursors.cursor(wedges, hover=True)
        FigureCanvasTkAgg(fig2, master=graph_frame).get_tk_widget().grid(row=0, column=1, padx=8, pady=8, sticky="nsew")
        self.store_last_fig(fig2)

        # --- 3. Top 10 Produits ---
        fig3, ax3 = plt.subplots(figsize=fig_size)
        top_products = self.data.groupby('produit')['montant_total'].sum().nlargest(10)
        bars3 = ax3.barh(top_products.index, top_products.values,
                         color=sns.color_palette("Blues_r", 10))
        ax3.set_title("Top 10 Produits", fontsize=11)
        ax3.tick_params(axis='y', labelsize=7)
        mplcursors.cursor(bars3, hover=True)
        FigureCanvasTkAgg(fig3, master=graph_frame).get_tk_widget().grid(row=0, column=2, padx=8, pady=8, sticky="nsew")
        self.store_last_fig(fig3)

        # --- 4. Fidélisation vs churn ---
        fig4, ax4 = plt.subplots(figsize=fig_size)
        churn = (self.data['note_satisfaction'] < 2).sum()
        fidel = len(self.data) - churn
        bars4 = ax4.bar(["Fidèles", "Churn"], [fidel, churn],
                        color=["#27ae60", "#e74c3c"])
        ax4.set_title("Fidélisation vs Churn", fontsize=11)
        mplcursors.cursor(bars4, hover=True)
        FigureCanvasTkAgg(fig4, master=graph_frame).get_tk_widget().grid(row=1, column=0, padx=8, pady=8, sticky="nsew")
        self.store_last_fig(fig4)

        # --- 5. Répartition par catégorie ---
        fig5, ax5 = plt.subplots(figsize=fig_size)
        cat_counts = self.data['catégorie'].value_counts().nlargest(8)
        bars5 = ax5.bar(cat_counts.index, cat_counts.values,
                        color=sns.color_palette("muted"))
        ax5.set_title("Répartition par catégorie", fontsize=11)
        ax5.tick_params(axis='x', rotation=45, labelsize=7)
        mplcursors.cursor(bars5, hover=True)
        FigureCanvasTkAgg(fig5, master=graph_frame).get_tk_widget().grid(row=1, column=1, padx=8, pady=8, sticky="nsew")
        self.store_last_fig(fig5)

        # --- 6. Évolution mensuelle ---
        fig6, ax6 = plt.subplots(figsize=fig_size)
        self.data['date_achat'] = pd.to_datetime(self.data['date_achat'])
        monthly = self.data.groupby(self.data['date_achat'].dt.to_period("M"))['montant_total'].sum().tail(6)
        monthly.index = monthly.index.astype(str)
        line, = ax6.plot(monthly.index, monthly.values, marker="o", color="orange")
        ax6.set_title("Évolution (6 derniers mois)", fontsize=11)
        ax6.tick_params(axis='x', rotation=45, labelsize=7)
        ax6.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " ")))
        cursor = mplcursors.cursor(line, hover=True)
        @cursor.connect("add")
        def on_add(sel):
            sel.annotation.set_text(f"{int(sel.target[1]):,} FCFA".replace(",", " "))
        FigureCanvasTkAgg(fig6, master=graph_frame).get_tk_widget().grid(row=1, column=2, padx=8, pady=8, sticky="nsew")
        self.store_last_fig(fig6)
