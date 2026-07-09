import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showerror
from data_loader import load_data
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import mplcursors
import matplotlib.ticker as mticker
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


# ===================== Classe RFM =====================
class RFMPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.data = load_data()
        self.prepare_data()
        self.sort_directions = {}
        self.init_ui()

    def prepare_data(self):
        self.data['date_achat'] = pd.to_datetime(self.data['date_achat'], errors='coerce')
        self.data['montant_total'] = pd.to_numeric(self.data['montant_total'], errors='coerce').fillna(0)

        snapshot_date = self.data['date_achat'].max() + pd.Timedelta(days=1)

        rfm = self.data[self.data['montant_total'] > 0].groupby('client_id').agg({
            'date_achat': lambda x: (snapshot_date - x.max()).days,
            'achat_id': 'count',
            'montant_total': 'sum'
        }).rename(columns={
            'date_achat': 'Recence',
            'achat_id': 'Frequence',
            'montant_total': 'Montant'
        })

        self.rfm = rfm.reset_index()
        self.rfm['client_id'] = range(1, len(self.rfm) + 1)

        shared_data["rfm_results"] = self.rfm.copy()

    def init_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        # === Réinitialiser les graphiques avant d'en ajouter de nouveaux ===
        shared_data["figs"] = []

        # === Onglet Graphiques ===
        graph_tab = ttk.Frame(notebook)
        notebook.add(graph_tab, text="Graphiques")

        # KPIs
        kpi_frame = ttk.Frame(graph_tab)
        kpi_frame.pack(fill="x", pady=10)
        kpi_frame.columnconfigure((0, 1, 2, 3), weight=1)

        avg_rec = self.rfm['Recence'].mean()
        avg_freq = self.rfm['Frequence'].mean()
        avg_mont = self.rfm['Montant'].mean()
        best_client = self.rfm.loc[self.rfm['Montant'].idxmax(), 'client_id']

        kpis = [
            ("📅 Récence Moy.", f"{avg_rec:.1f} j"),
            ("🔁 Fréquence Moy.", f"{avg_freq:.1f}"),
            ("💰 Montant Moy.", f"{avg_mont:,.0f} FCFA"),
            ("⭐ Top Client", f"ID {best_client}"),
        ]
        for i, (label, value) in enumerate(kpis):
            card = create_kpi_card(kpi_frame, label, value)
            card.grid(row=0, column=i, padx=10, sticky="nsew")

        # Grille des graphiques
        graph_frame = ttk.Frame(graph_tab)
        graph_frame.pack(fill="both", expand=True, padx=10, pady=10)

        for i in range(2):
            graph_frame.rowconfigure(i, weight=1, uniform="row")
        for j in range(3):
            graph_frame.columnconfigure(j, weight=1, uniform="col")

        fig_size = (4.5, 3.5)

        # 1. Scatter Récence vs Montant
        fig1, ax1 = plt.subplots(figsize=fig_size)
        scatter1 = ax1.scatter(self.rfm['Recence'], self.rfm['Montant'], alpha=0.7, c='green')
        ax1.set_title("Récence vs Montant")
        ax1.set_xlabel("Récence (jours)")
        ax1.set_ylabel("Montant total")
        ax1.tick_params(axis="both", labelsize=7)
        ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " ")))
        mplcursors.cursor(scatter1, hover=True)
        fig1.tight_layout()
        self._add_figure_to_frame(fig1, graph_frame, 0, 0)

        # 2. Scatter Fréquence vs Montant
        fig2, ax2 = plt.subplots(figsize=fig_size)
        scatter2 = ax2.scatter(self.rfm['Frequence'], self.rfm['Montant'], alpha=0.7, c='orange')
        ax2.set_title("Fréquence vs Montant")
        ax2.set_xlabel("Fréquence")
        ax2.set_ylabel("Montant total")
        ax2.tick_params(axis="both", labelsize=7)
        ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " ")))
        mplcursors.cursor(scatter2, hover=True)
        fig2.tight_layout()
        self._add_figure_to_frame(fig2, graph_frame, 0, 1)

        # 3. Histogramme Récence
        fig3, ax3 = plt.subplots(figsize=fig_size)
        ax3.hist(self.rfm['Recence'], bins=20, color='blue', edgecolor='black')
        ax3.set_title("Distribution de la récence")
        ax3.set_xlabel("Récence (jours)")
        ax3.set_ylabel("Clients")
        ax3.tick_params(axis="both", labelsize=7)
        mplcursors.cursor(ax3.patches, hover=True)
        fig3.tight_layout()
        self._add_figure_to_frame(fig3, graph_frame, 0, 2)

        # 4. Histogramme Fréquence
        fig4, ax4 = plt.subplots(figsize=fig_size)
        ax4.hist(self.rfm['Frequence'], bins=20, color='purple', edgecolor='black')
        ax4.set_title("Distribution de la fréquence")
        ax4.set_xlabel("Fréquence")
        ax4.set_ylabel("Clients")
        ax4.tick_params(axis="both", labelsize=7)
        mplcursors.cursor(ax4.patches, hover=True)
        fig4.tight_layout()
        self._add_figure_to_frame(fig4, graph_frame, 1, 0)

        # 5. Histogramme Montant
        fig5, ax5 = plt.subplots(figsize=fig_size)
        ax5.hist(self.rfm['Montant'], bins=20, color='red', edgecolor='black')
        ax5.set_title("Distribution du montant")
        ax5.set_xlabel("Montant total")
        ax5.set_ylabel("Clients")
        ax5.tick_params(axis="both", labelsize=7)
        ax5.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " ")))
        mplcursors.cursor(ax5.patches, hover=True)
        fig5.tight_layout()
        self._add_figure_to_frame(fig5, graph_frame, 1, 1)

        # 6. Boxplot Montant avec annotations
        fig6, ax6 = plt.subplots(figsize=fig_size)
        box = ax6.boxplot(self.rfm['Montant'], vert=False, patch_artist=True,
                          boxprops=dict(facecolor="skyblue"))
        ax6.set_title("Boxplot du montant")
        ax6.set_xlabel("Montant total")
        ax6.tick_params(axis="both", labelsize=7)
        ax6.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " ")))

        # Calculer Q1, médiane, Q3
        q1 = self.rfm['Montant'].quantile(0.25)
        median = self.rfm['Montant'].median()
        q3 = self.rfm['Montant'].quantile(0.75)

        ax6.annotate(f"Q1: {q1:,.0f}", xy=(q1, 1), xytext=(q1, 1.05),
                     ha="center", fontsize=7, color="blue", rotation=45)
        ax6.annotate(f"Médiane: {median:,.0f}", xy=(median, 1), xytext=(median, 1.1),
                     ha="center", fontsize=7, color="green", rotation=45)
        ax6.annotate(f"Q3: {q3:,.0f}", xy=(q3, 1), xytext=(q3, 1.05),
                     ha="center", fontsize=7, color="red", rotation=45)

        mplcursors.cursor(ax6.artists + ax6.lines, hover=True)
        fig6.tight_layout()
        self._add_figure_to_frame(fig6, graph_frame, 1, 2)

        # === Onglet Tableau ===
        frame_table = ttk.Frame(notebook)
        notebook.add(frame_table, text="Tableau")

        table_frame = ttk.Frame(frame_table)
        table_frame.pack(fill="both", expand=True)

        tree_scroll_y = ttk.Scrollbar(table_frame, orient="vertical")
        tree_scroll_y.pack(side="right", fill="y")

        tree_scroll_x = ttk.Scrollbar(table_frame, orient="horizontal")
        tree_scroll_x.pack(side="bottom", fill="x")

        self.table = ttk.Treeview(
            table_frame,
            columns=list(self.rfm.columns),
            show="headings",
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set
        )
        self.table.pack(fill="both", expand=True)

        tree_scroll_y.config(command=self.table.yview)
        tree_scroll_x.config(command=self.table.xview)

        for col in self.rfm.columns:
            self.sort_directions[col] = False
            self.table.heading(col, text=col, command=lambda c=col: self.sort_column(c))
            max_width = max([len(str(val)) for val in self.rfm[col]]) * 8
            self.table.column(col, anchor="center", width=max(80, min(max_width, 300)))

        self.display_table(self.rfm)

    def sort_column(self, col):
        reverse = self.sort_directions[col]
        try:
            sorted_df = self.rfm.sort_values(by=col, ascending=not reverse)
        except Exception as e:
            showerror("Erreur de tri", str(e))
            return
        self.sort_directions[col] = not reverse
        self.display_table(sorted_df)

    def display_table(self, df):
        for item in self.table.get_children():
            self.table.delete(item)
        for _, row in df.iterrows():
            self.table.insert("", tk.END, values=list(row))

    def _add_figure_to_frame(self, fig, frame, row, column):
        """Affiche le graphique et l'ajoute à shared_data pour l'export"""
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=row, column=column, padx=10, pady=10, sticky="nsew")

        # 🔹 Sauvegarde globale pour export
        if "figs" not in shared_data:
            shared_data["figs"] = []
        shared_data["figs"].append(fig)
