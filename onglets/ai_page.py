import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import mplcursors

from data_loader import load_data
from shared_data import shared_data


# ========= Fonction utilitaire pour créer une carte KPI =========
def create_kpi_card(parent, title, value, bg_color="#2c2c3c", hover_color="#3d3d5c"):
    frame = tk.Frame(parent, bg=bg_color, bd=0, relief="flat", width=160, height=80)
    frame.pack_propagate(False)

    label_title = tk.Label(frame, text=title, font=("Segoe UI", 10, "bold"),
                           fg="white", bg=bg_color)
    label_title.pack(pady=(5, 0))

    label_value = tk.Label(frame, text=value, font=("Segoe UI", 12, "bold"),
                           fg="#00cec9", bg=bg_color)
    label_value.pack(pady=(0, 5))

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


# ===================== Classe IA =====================
class AIPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.data = load_data()
        if self.data is None or self.data.empty:
            messagebox.showerror("Erreur", "Aucune donnée disponible.")
            return

        shared_data["figs"] = []  # nécessaire pour export

        # Layout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)  # KPIs
        self.rowconfigure(1, weight=0)  # Recherche
        self.rowconfigure(2, weight=1)  # Notebook

        # KPIs
        self._build_kpis()

        # Zone utilisateur
        self._build_query_zone()

        # Notebook résultats
        self._build_notebook()

    # ===================== Construction des KPIs =====================
    def _build_kpis(self):
        kpi_frame = ttk.Frame(self)
        kpi_frame.grid(row=0, column=0, pady=15, sticky="ew")
        kpi_frame.columnconfigure((0, 1, 2, 3), weight=1)

        total_ca = self.data["montant_total"].sum()
        retour_rate = (self.data["retour"] == 1).mean() * 100
        repeat_rate = self.data.groupby("client_id").size().gt(1).mean() * 100
        best_product = self.data.groupby("produit")["montant_total"].sum().idxmax()

        kpis = [
            ("💰 CA Total", f"{total_ca:,.0f} FCFA"),
            ("🔄 Taux de retour", f"{retour_rate:.2f}%"),
            ("👥 Fidélité clients", f"{repeat_rate:.2f}%"),
            ("🏆 Produit phare", best_product),
        ]

        for i, (label, value) in enumerate(kpis):
            card = create_kpi_card(kpi_frame, label, value)
            card.grid(row=0, column=i, padx=10, sticky="nsew")

    # ===================== Zone de recherche =====================
    def _build_query_zone(self):
        query_label = ttk.Label(self, text="💡 Posez votre question marketing :",
                                font=("Segoe UI", 11, "bold"), foreground="#1a2b49")
        query_label.grid(row=1, column=0, sticky="w", padx=10, pady=5)

        frame = ttk.Frame(self)
        frame.grid(row=1, column=0, sticky="ew", padx=10)
        frame.columnconfigure(0, weight=1)

        self.query_entry = ttk.Entry(frame, width=80)
        self.query_entry.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        ask_button = ttk.Button(frame, text="Analyser", command=self.process_query)
        ask_button.grid(row=0, column=1, padx=5, pady=5)

    # ===================== Notebook résultats =====================
    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)

        self.text_tab = ttk.Frame(self.notebook)
        self.graph_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.text_tab, text="📊 Analyse & Recommandations")
        self.notebook.add(self.graph_tab, text="📈 Graphique")

        # Zone texte analyse
        self.answer_text = tk.Text(
            self.text_tab, wrap="word", height=15, width=100,
            bg="#ffffff", fg="#333333", relief="flat", bd=1, font=("Segoe UI", 10)
        )
        self.answer_text.pack(fill="both", expand=True, padx=10, pady=10)

        # Frame graphique
        self.chart_frame = ttk.Frame(self.graph_tab)
        self.chart_frame.pack(fill="both", expand=True)

    # ===================== Analyse des questions =====================
    def process_query(self):
        query = self.query_entry.get().strip().lower()
        if not query:
            messagebox.showwarning("Avertissement", "Veuillez entrer une question.")
            return

        # Reset zones
        self.answer_text.delete("1.0", tk.END)
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        shared_data["figs"].clear()

        response = ""
        recommendation = ""
        fig = None

        # Exemple simple de moteur de règles
        if "produit" in query:
            top_products = self.data.groupby("produit")["montant_total"].sum().nlargest(10)
            response = f"Top produits par chiffre d'affaires :\n\n{top_products.to_string()}"
            recommendation = "📌 Recommandation : Renforcer la mise en avant et les promotions des produits en tête."
            fig, ax = plt.subplots(figsize=(6, 4))
            bars = ax.barh(top_products.index[::-1], top_products.values[::-1], color=sns.color_palette("Blues_r", 10))
            ax.set_title("Top 10 Produits")
            mplcursors.cursor(bars, hover=True)

        elif "ville" in query:
            city_sales = self.data.groupby("ville")["montant_total"].sum().nlargest(10)
            response = f"Top villes en termes de CA :\n\n{city_sales.to_string()}"
            recommendation = "📌 Recommandation : Renforcer la présence commerciale dans les villes les plus rentables."
            fig, ax = plt.subplots(figsize=(6, 4))
            bars = ax.bar(city_sales.index, city_sales.values, color=sns.color_palette("Set2"))
            ax.set_title("Top Villes")
            ax.tick_params(axis="x", rotation=45)
            mplcursors.cursor(bars, hover=True)

        elif "client" in query or "fidélité" in query:
            repeat_rate = self.data.groupby("client_id").size().gt(1).mean() * 100
            response = f"Taux de fidélité : {repeat_rate:.2f}%"
            recommendation = "📌 Recommandation : Lancer un programme de fidélité pour augmenter ce taux."
            fig, ax = plt.subplots(figsize=(5, 4))
            bars = ax.bar(["Fidélité"], [repeat_rate], color="#27ae60")
            ax.set_ylim(0, 100)
            mplcursors.cursor(bars, hover=True)

        elif "revenu" in query or "chiffre" in query or "ca" in query:
            monthly = self.data.groupby(self.data["date_achat"].dt.to_period("M"))["montant_total"].sum().tail(6)
            response = f"Revenus des 6 derniers mois :\n\n{monthly.to_string()}"
            recommendation = "📌 Recommandation : Augmenter les ventes via des promotions ciblées."
            fig, ax = plt.subplots(figsize=(6, 4))
            line, = ax.plot(monthly.index.astype(str), monthly.values, marker="o", color="orange")
            ax.set_title("Revenus Mensuels")
            mplcursors.cursor(line, hover=True)

        else:
            response = "❓ Question non reconnue. Essayez par ex. : 'top produits', 'CA', 'fidélité clients', 'top villes'."
            recommendation = "📌 Recommandation : Poser une question plus spécifique."

        # Affichage analyse + reco
        self.answer_text.insert("1.0", f"{response}\n\n{recommendation}")

        # Graphique
        if fig:
            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            shared_data["figs"].append(fig)
