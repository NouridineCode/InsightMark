import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from datetime import datetime
import pandas as pd

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import dates as mdates
import mplcursors

from data_loader import load_data
from shared_data import shared_data


class FilterPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        # Données
        self.data = load_data()
        self.filtered_data = self.data.copy()
        self.current_graph_col = 'montant_total'

        # UI
        self.init_ui()

        # Stockage initial
        shared_data["filters"] = self.filtered_data.copy()
        shared_data["figs"] = [self.fig]   # 🔹 Sauvegarde figure pour export

    # ---------------- UI ----------------
    def init_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        # Titre stylisé
        title = ttk.Label(
            self, text="🔍 Filtrer les données clients",
            font=("Segoe UI", 16, "bold"), foreground="#004080"
        )
        title.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # --- Cadre Filtres ---
        self.filter_frame = ttk.LabelFrame(self, text="Filtres", padding=10)
        self.filter_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        # Segment
        ttk.Label(self.filter_frame, text="Segment:").grid(row=0, column=0, padx=5, pady=5)
        segments = [''] + (list(self.data['segment'].dropna().unique()) if 'segment' in self.data.columns else [])
        self.segment_var = tk.StringVar()
        self.segment_combo = ttk.Combobox(self.filter_frame, textvariable=self.segment_var,
                                          values=segments, state="readonly", width=15)
        self.segment_combo.grid(row=0, column=1, padx=5, pady=5)

        # Sexe
        ttk.Label(self.filter_frame, text="Sexe:").grid(row=0, column=2, padx=5, pady=5)
        self.sexe_var = tk.StringVar()
        self.sexe_combo = ttk.Combobox(self.filter_frame, textvariable=self.sexe_var,
                                       values=["", "Homme", "Femme"], state="readonly", width=10)
        self.sexe_combo.grid(row=0, column=3, padx=5, pady=5)

        # Dates
        ttk.Label(self.filter_frame, text="Date début:").grid(row=1, column=0, padx=5, pady=5)
        self.date_debut_entry = DateEntry(self.filter_frame, date_pattern='yyyy-MM-dd', width=12)
        self.date_debut_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(self.filter_frame, text="Date fin:").grid(row=1, column=2, padx=5, pady=5)
        self.date_fin_entry = DateEntry(self.filter_frame, date_pattern='yyyy-MM-dd', width=12)
        self.date_fin_entry.grid(row=1, column=3, padx=5, pady=5)

        # Bouton appliquer
        self.apply_button = ttk.Button(self.filter_frame, text="🔍 Appliquer le filtre", command=self.apply_filters)
        self.apply_button.grid(row=0, column=4, rowspan=2, padx=15, pady=5)

        # --- Notebook ---
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=4, column=0, sticky="nsew", padx=10, pady=10)

        self.tab_data = ttk.Frame(self.notebook)
        self.tab_graph = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_data, text="📊 Données")
        self.notebook.add(self.tab_graph, text="📈 Graphique")

        # --- Table ---
        self.tree = ttk.Treeview(self.tab_data, columns=list(self.data.columns), show="headings", height=15)
        for col in self.data.columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_treeview(c, False))
            self.tree.column(col, width=110, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(self.tab_data, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.tab_data, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        self.tab_data.rowconfigure(0, weight=1)
        self.tab_data.columnconfigure(0, weight=1)

        # --- Graphique ---
        self.fig, self.ax = plt.subplots(figsize=(8, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_graph)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Affichage initial
        self.populate_table(self.data)
        self.update_graph(self.filtered_data, self.current_graph_col)

    # ---------------- Data table ----------------
    def populate_table(self, df: pd.DataFrame):
        self.tree.delete(*self.tree.get_children())
        for _, row in df.iterrows():
            values = ["" if pd.isna(v) else v for v in row]
            self.tree.insert("", "end", values=values)

    # ---------------- Filtres ----------------
    def apply_filters(self):
        df = self.data.copy()

        # Segment
        seg = self.segment_var.get()
        if seg and 'segment' in df.columns:
            df = df[df['segment'] == seg]

        # Sexe
        sx = self.sexe_var.get()
        if sx and 'sexe' in df.columns:
            df = df[df['sexe'] == sx]

        # Dates
        try:
            date_debut_str = self.date_debut_entry.get()
            date_fin_str = self.date_fin_entry.get()
            if date_debut_str:
                date_debut = datetime.strptime(date_debut_str, "%Y-%m-%d")
                df = df[pd.to_datetime(df['date_achat'], errors='coerce') >= date_debut]
            if date_fin_str:
                date_fin = datetime.strptime(date_fin_str, "%Y-%m-%d")
                df = df[pd.to_datetime(df['date_achat'], errors='coerce') <= date_fin]
        except Exception as e:
            print("Erreur date :", e)

        if 'date_achat' in df.columns and 'montant_total' in df.columns:
            df = df.sort_values(by=['date_achat', 'montant_total'])

        self.filtered_data = df
        shared_data["filters"] = self.filtered_data.copy()

        self.populate_table(df)
        self.update_graph(df, self.current_graph_col)

    # ---------------- Tri ----------------
    def sort_treeview(self, col, descending):
        df_sorted = self.filtered_data.copy()
        if col not in df_sorted.columns:
            return

        if col in ['âge', 'quantité', 'montant_total', 'prix_unitaire', 'retour', 'note_satisfaction', 'propension_achat']:
            df_sorted[col] = pd.to_numeric(df_sorted[col], errors='coerce')
            df_sorted = df_sorted.sort_values(by=col, ascending=not descending, na_position='last')
        elif col == 'date_achat':
            df_sorted[col] = pd.to_datetime(df_sorted[col], errors='coerce')
            df_sorted = df_sorted.sort_values(by=col, ascending=not descending, na_position='last')
        else:
            df_sorted[col] = df_sorted[col].astype(str)
            df_sorted = df_sorted.sort_values(by=col, key=lambda x: x.str.lower(), ascending=not descending)

        self.filtered_data = df_sorted
        shared_data["filters"] = self.filtered_data.copy()
        self.populate_table(df_sorted)

        self.current_graph_col = col
        self.update_graph(df_sorted, col)

        self.tree.heading(col, command=lambda: self.sort_treeview(col, not descending))

    # ---------------- Graphique ----------------
    def update_graph(self, df, col):
        self.ax.clear()

        if df.empty:
            self.ax.text(0.5, 0.5, "Pas de données à afficher",
                         ha="center", va="center", transform=self.ax.transAxes, color="red")
            self.canvas.draw_idle()
            shared_data["figs"] = [self.fig]
            shared_data["filters"] = df.copy()
            return

        # Série temporelle
        if col in ['date_achat', 'montant_total'] and {'date_achat', 'montant_total'}.issubset(df.columns):
            df_plot = df.copy()
            df_plot['date_achat'] = pd.to_datetime(df_plot['date_achat'], errors='coerce')
            df_plot = df_plot.dropna(subset=['date_achat', 'montant_total'])
            if not df_plot.empty:
                montant_par_date = df_plot.groupby('date_achat')['montant_total'].sum().sort_index()
                x_dates = montant_par_date.index
                y = montant_par_date.values
                line, = self.ax.plot_date(x_dates, y, linestyle='-', marker='o', color="#004080")

                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                self.fig.autofmt_xdate()

                self.ax.set_title("Montant total des achats au fil du temps", color="#004080", fontsize=12, fontweight="bold")
                self.ax.set_xlabel("Date d'achat")
                self.ax.set_ylabel("Montant total")
                self.ax.grid(True, linestyle="--", alpha=0.6)

                cursor = mplcursors.cursor(line, hover=True)
                @cursor.connect("add")
                def on_add(sel):
                    date_val = mdates.num2date(sel.target[0]).strftime('%Y-%m-%d')
                    montant_val = f"{sel.target[1]:,.0f} FCFA"
                    sel.annotation.set_text(f"Date: {date_val}\nMontant: {montant_val}")

                self.canvas.draw_idle()
                shared_data["figs"] = [self.fig]
                shared_data["filters"] = df.copy()
                return

        # Histogramme
        if col in df.columns and pd.api.types.is_numeric_dtype(pd.to_numeric(df[col], errors='coerce')):
            df_col = pd.to_numeric(df[col], errors='coerce').dropna()
            if not df_col.empty:
                bars = self.ax.hist(df_col, bins=15, alpha=0.7, color="#007acc")
                self.ax.set_title(f'Distribution de "{col}"', color="#004080", fontsize=12, fontweight="bold")
                self.ax.set_xlabel(col)
                self.ax.set_ylabel('Effectif')
                self.ax.grid(True, linestyle="--", alpha=0.6)

                cursor = mplcursors.cursor(self.ax.patches, hover=True)
                @cursor.connect("add")
                def on_add(sel):
                    sel.annotation.set_text(f"{sel.target[1]:,.0f} FCFA")

                self.canvas.draw_idle()
                shared_data["figs"] = [self.fig]
                shared_data["filters"] = df.copy()
                return

        # Barplot
        if col in df.columns and (pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_categorical_dtype(df[col])):
            df_col = df[col].astype(str).dropna()
            if not df_col.empty:
                top_counts = df_col.value_counts().nlargest(10)
                bars = self.ax.bar(top_counts.index, top_counts.values, color="#009688")
                self.ax.set_title(f'Top 10 valeurs de "{col}"', color="#004080", fontsize=12, fontweight="bold")
                self.ax.set_xlabel(col)
                self.ax.set_ylabel('Nombre')
                self.ax.tick_params(axis='x', rotation=30)
                self.ax.grid(axis='y', linestyle="--", alpha=0.6)

                cursor = mplcursors.cursor(bars, hover=True)
                @cursor.connect("add")
                def on_add(sel):
                    sel.annotation.set_text(f"{int(sel.target[1]):,d} FCFA")

                self.canvas.draw_idle()
                shared_data["figs"] = [self.fig]
                shared_data["filters"] = df.copy()
                return

        # Cas aucun graphique possible
        self.ax.text(0.5, 0.5, f"Aucune donnée pour '{col}'",
                     ha="center", va="center", transform=self.ax.transAxes, color="red")
        self.canvas.draw_idle()
        shared_data["figs"] = [self.fig]
        shared_data["filters"] = df.copy()
