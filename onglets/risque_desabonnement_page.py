import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
import mplcursors

from shared_data import shared_data
from data_loader import load_data


class RisqueDesabonnementPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.data = load_data()
        if self.data is None or self.data.empty:
            ttk.Label(self, text="Aucune donnée disponible.", font=("Segoe UI", 14)).pack(pady=20)
            return

        self._prepare_data()
        shared_data["churn_risk"] = self.data.copy()
        shared_data["figs"] = []   # 🔹 reset des figures pour export

        self.current_fig = None
        self.current_canvas = None
        self.current_cursor = None

        self.init_ui()

    # ------------------------------------------------------------------
    def _prepare_data(self):
        """Calcule un score de risque basé sur RFM."""
        self.data["date_achat"] = pd.to_datetime(self.data["date_achat"], errors="coerce")
        snapshot_date = self.data["date_achat"].max() + pd.Timedelta(days=1)

        rfm = self.data.groupby("client_id").agg({
            "date_achat": lambda x: (snapshot_date - x.max()).days,
            "achat_id": "count" if "achat_id" in self.data.columns else "size",
            "montant_total": "sum"
        }).rename(columns={"date_achat": "Recence", "achat_id": "Frequence", "montant_total": "Montant"})

        # Score de risque (0-100)
        rfm["Score"] = (
            (rfm["Recence"].rank(pct=True) * 40) +
            (rfm["Frequence"].rank(pct=True, ascending=False) * 30) +
            (rfm["Montant"].rank(pct=True, ascending=False) * 30)
        )
        rfm["Score"] = rfm["Score"].round(0)

        def categ(score):
            if score >= 70:
                return "Élevé"
            elif score >= 40:
                return "Modéré"
            else:
                return "Faible"

        rfm["Risque"] = rfm["Score"].apply(categ)
        self.data = rfm.reset_index()

    # ------------------------------------------------------------------
    def init_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        # Onglets
        frame_table = ttk.Frame(notebook)
        frame_graphs = ttk.Frame(notebook)

        notebook.add(frame_table, text="Tableau récapitulatif")
        notebook.add(frame_graphs, text="Graphiques")

        self._build_table_tab(frame_table)
        self._build_graphs_tab(frame_graphs)

    # ------------------------------------------------------------------
    def _build_table_tab(self, parent):
        # === KPIs ===
        kpi_frame = ttk.Frame(parent)
        kpi_frame.pack(fill="x", pady=8)

        total_clients = self.data["client_id"].nunique()
        pct_high = (self.data["Risque"] == "Élevé").mean() * 100
        revenu_high = self.data.loc[self.data["Risque"] == "Élevé", "Montant"].sum()

        self._add_kpi(kpi_frame, "Total clients", f"{total_clients}", "skyblue", 0)
        self._add_kpi(kpi_frame, "% à haut risque", f"{pct_high:.1f} %", "orange", 1)
        self._add_kpi(kpi_frame, "Revenu haut risque", f"{revenu_high:,.0f} FCFA", "lightgreen", 2)

        # === Tableau ===
        cols = ["client_id", "Recence", "Frequence", "Montant", "Score", "Risque"]
        self.tree = ttk.Treeview(parent, columns=cols, show="headings")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)

        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=120)

        for _, row in self.data.iterrows():
            self.tree.insert("", "end", values=[row[c] for c in cols])

        # clic sur une ligne → popup détail
        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)

    def _add_kpi(self, parent, title, value, color, col):
        frame = tk.Frame(parent, bg=color, bd=1, relief="raised")
        frame.grid(row=0, column=col, padx=10, pady=5, sticky="nsew")
        tk.Label(frame, text=title, bg=color, font=("Segoe UI", 10, "bold")).pack(padx=20, pady=(5, 0))
        tk.Label(frame, text=value, bg=color, font=("Segoe UI", 12, "bold")).pack(padx=20, pady=(0, 10))
        parent.columnconfigure(col, weight=1)

    def _on_row_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        client_id = item["values"][0]
        self._open_client_detail(client_id)

    def _open_client_detail(self, client_id):
        df_client = self.data[self.data["client_id"] == client_id]
        if df_client.empty:
            messagebox.showinfo("Détails client", f"Aucun historique pour le client {client_id}")
            return

        top = tk.Toplevel(self)
        top.title(f"Détails client {client_id}")
        top.geometry("700x400")

        recap = f"Client {client_id}\n" \
                f"Transactions : {df_client['Frequence'].iloc[0]}\n" \
                f"Montant cumulé : {df_client['Montant'].iloc[0]:,.0f} FCFA\n" \
                f"Score : {df_client['Score'].iloc[0]}\n" \
                f"Risque : {df_client['Risque'].iloc[0]}"

        ttk.Label(top, text=recap, justify="left").pack(anchor="w", padx=10, pady=10)

    # ------------------------------------------------------------------
    def _build_graphs_tab(self, parent):
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)

        menu = ttk.Frame(parent, width=220)
        menu.grid(row=0, column=0, sticky="ns")
        menu.grid_propagate(False)

        self.plot_frame = ttk.Frame(parent)
        self.plot_frame.grid(row=0, column=1, sticky="nsew")

        graphs = [
            ("Histogramme des scores", self._plot_histogram),
            ("Scatter Montant vs Recence", self._plot_scatter),
            ("Répartition des risques", self._plot_pie)
        ]

        for title, func in graphs:
            b = ttk.Button(menu, text=title, command=lambda f=func: self._show_plot(f))
            b.pack(fill="x", padx=6, pady=4)

        # Par défaut afficher le premier
        self._show_plot(graphs[0][1])

    def _clear_plot_area(self):
        if self.current_canvas:
            self.current_canvas.get_tk_widget().destroy()
        if self.current_fig:
            plt.close(self.current_fig)
        self.current_fig = None
        self.current_canvas = None
        self.current_cursor = None

    def _show_plot(self, func):
        self._clear_plot_area()
        fig = func()
        if fig:
            self.current_fig = fig
            canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            self.current_canvas = canvas

            # 🔹 Sauvegarde pour export
            shared_data["figs"].append(fig)

    # ------------------------------------------------------------------
    # Graphiques
    def _plot_histogram(self):
        fig, ax = plt.subplots(figsize=(7, 4))
        bars = ax.hist(self.data["Score"], bins=10, color="skyblue", edgecolor="black")
        ax.set_title("Distribution des scores de risque")
        ax.set_xlabel("Score")
        ax.set_ylabel("Clients")

        cursor = mplcursors.cursor(ax.patches, hover=True)
        @cursor.connect("add")
        def on_add(sel):
            sel.annotation.set_text(f"{int(sel.artist.get_height())} clients")

        self.current_cursor = cursor
        return fig

    def _plot_scatter(self):
        fig, ax = plt.subplots(figsize=(7, 5))
        scatter = ax.scatter(self.data["Recence"], self.data["Montant"],
                             c=self.data["Score"], cmap="coolwarm", alpha=0.7)
        ax.set_title("Montant vs Récence (coloré par score)")
        ax.set_xlabel("Récence (jours)")
        ax.set_ylabel("Montant")
        plt.colorbar(scatter, ax=ax, label="Score de risque")

        cursor = mplcursors.cursor(scatter, hover=True)
        @cursor.connect("add")
        def on_add(sel):
            x, y = sel.target
            sel.annotation.set_text(f"Recence={x:.0f}\nMontant={y:,.0f} FCFA")

        self.current_cursor = cursor
        return fig

    def _plot_pie(self):
        s = self.data["Risque"].value_counts()
        fig, ax = plt.subplots(figsize=(6, 4))
        wedges, _, _ = ax.pie(s, labels=s.index, autopct="%1.1f%%", startangle=90, colors=plt.cm.Set3.colors)
        ax.set_title("Répartition des clients par niveau de risque")

        cursor = mplcursors.cursor(wedges, hover=True)
        @cursor.connect("add")
        def on_add(sel):
            idx = sel.index
            sel.annotation.set_text(f"{s.index[idx]} : {s.values[idx]} clients")

        self.current_cursor = cursor
        return fig
