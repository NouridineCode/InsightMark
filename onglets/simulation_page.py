# onglets/simulation_page.py
import tkinter as tk
from tkinter import ttk, simpledialog
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import mplcursors
import matplotlib.ticker as mticker

from data_loader import load_data
from shared_data import shared_data

# ---- Styles / couleurs ----
PRIMARY_BTN_BG = "#00cec9"   # turquoise action principale
PRIMARY_BTN_FG = "black"
SECONDARY_BTN_BG = "#2c2c3c"
SECONDARY_BTN_FG = "white"
KPI_BG = "#2c2c3c"
KPI_FG = "#00cec9"

def format_fcfa(x):
    try:
        return f"{int(x):,}".replace(",", " ") + " FCFA"
    except:
        return str(x)

class SimulationPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.data = load_data()
        # init shared storage for three types
        for t in ("marketing", "statistique", "comportementale"):
            key = f"sim_results_{t}"
            if shared_data.get(key) is None:
                shared_data[key] = pd.DataFrame()
        self.sort_directions = {}
        self.current_type = tk.StringVar(value="marketing")
        self._build_ui()
        self.update_display()

    # ---------------- UI ----------------
    def _build_ui(self):
        # Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        # Form tab
        self.tab_form = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_form, text="Formulaire")

        title = ttk.Label(self.tab_form, text="📊 Simulations — Marketing / Statistique / Comportementale",
                          font=("Segoe UI", 14, "bold"))
        title.pack(pady=(10,6))

        # Type selector
        type_frame = ttk.Frame(self.tab_form)
        type_frame.pack(fill="x", padx=12)
        ttk.Label(type_frame, text="Type de simulation:", font=("Segoe UI", 10, "bold")).pack(side="left")
        type_combo = ttk.Combobox(type_frame, textvariable=self.current_type,
                                  values=["marketing", "statistique", "comportementale"], state="readonly", width=20)
        type_combo.pack(side="left", padx=8)
        type_combo.bind("<<ComboboxSelected>>", lambda e: self._render_form_fields())

        # form dynamic area
        self.form_frame = ttk.Frame(self.tab_form)
        self.form_frame.pack(fill="x", padx=12, pady=10)

        # action buttons
        action_frame = ttk.Frame(self.tab_form)
        action_frame.pack(fill="x", padx=12, pady=(0,8))

        self.run_btn = tk.Button(action_frame, text="Lancer la simulation",
                                 bg=PRIMARY_BTN_BG, fg=PRIMARY_BTN_FG, bd=0,
                                 font=("Segoe UI", 10, "bold"), command=self._run_simulation)
        self.run_btn.pack(side="left", padx=(0,8))

        # scenarios button
        self.scenario_btn = tk.Button(action_frame, text="Charger scénarios prédéfinis",
                                      bg=SECONDARY_BTN_BG, fg=SECONDARY_BTN_FG, bd=0,
                                      command=self._open_scenario_dialog)
        self.scenario_btn.pack(side="left", padx=8)

        # clear history button
        self.clear_btn = tk.Button(action_frame, text="Effacer historique", bg=SECONDARY_BTN_BG,
                                   fg=SECONDARY_BTN_FG, bd=0, command=self._clear_current)
        self.clear_btn.pack(side="left", padx=8)

        # KPI frame
        self.kpi_frame = ttk.Frame(self.tab_form)
        self.kpi_frame.pack(fill="x", padx=12, pady=(4, 12))

        # Graphs tab
        self.tab_graph = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_graph, text="Graphiques")
        self.graph_frame = ttk.Frame(self.tab_graph)
        self.graph_frame.pack(fill="both", expand=True, padx=8, pady=8)
        for r in range(2):
            self.graph_frame.rowconfigure(r, weight=1)
        for c in range(2):
            self.graph_frame.columnconfigure(c, weight=1)

        # Table tab
        self.tab_table = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_table, text="Tableau")
        self.table_frame = ttk.Frame(self.tab_table)
        self.table_frame.pack(fill="both", expand=True, padx=8, pady=8)

        # initial form rendering
        self._render_form_fields()

    # ---------------- Dynamic form ----------------
    def _render_form_fields(self):
        for w in self.form_frame.winfo_children():
            w.destroy()
        t = self.current_type.get()

        # historical averages
        try:
            avg_price = float(self.data['prix_unitaire'].mean())
        except Exception:
            avg_price = 1000.0

        if t == "marketing":
            ttk.Label(self.form_frame, text="% Remise:", width=20).grid(row=0, column=0, sticky="w", padx=4, pady=6)
            self.remise_var = tk.DoubleVar(value=10.0)
            self.remise_spin = ttk.Spinbox(self.form_frame, from_=0, to=100, increment=1, textvariable=self.remise_var, width=10)
            self.remise_spin.grid(row=0, column=1, padx=4, pady=6)

            ttk.Label(self.form_frame, text="Coût campagne (FCFA):").grid(row=0, column=2, sticky="w", padx=4, pady=6)
            self.cout_var = tk.DoubleVar(value=50000.0)
            self.cout_entry = ttk.Entry(self.form_frame, textvariable=self.cout_var, width=15)
            self.cout_entry.grid(row=0, column=3, padx=4, pady=6)

            ttk.Label(self.form_frame, text="Clients ciblés:").grid(row=1, column=0, sticky="w", padx=4, pady=6)
            self.clients_var = tk.IntVar(value=1000)
            self.clients_spin = ttk.Spinbox(self.form_frame, from_=1, to=1000000, increment=100, textvariable=self.clients_var, width=12)
            self.clients_spin.grid(row=1, column=1, padx=4, pady=6)

            ttk.Label(self.form_frame, text="Quantité moyenne par client:").grid(row=1, column=2, sticky="w", padx=4, pady=6)
            self.qty_var = tk.IntVar(value=1)
            self.qty_spin = ttk.Spinbox(self.form_frame, from_=1, to=100, increment=1, textvariable=self.qty_var, width=10)
            self.qty_spin.grid(row=1, column=3, padx=4, pady=6)

            ttk.Label(self.form_frame, text=f"Prix unitaire moyen (historique): {avg_price:,.0f} FCFA").grid(row=2, column=0, columnspan=4, sticky="w", padx=4, pady=(6,0))

        elif t == "statistique":
            ttk.Label(self.form_frame, text="Croissance attendue (%/mois):").grid(row=0, column=0, sticky="w", padx=4, pady=6)
            self.growth_var = tk.DoubleVar(value=2.0)
            self.growth_spin = ttk.Spinbox(self.form_frame, from_=-50, to=200, increment=0.5, textvariable=self.growth_var, width=12)
            self.growth_spin.grid(row=0, column=1, padx=4, pady=6)

            ttk.Label(self.form_frame, text="Horizon (mois):").grid(row=0, column=2, sticky="w", padx=4, pady=6)
            self.horizon_var = tk.IntVar(value=6)
            self.horizon_spin = ttk.Spinbox(self.form_frame, from_=1, to=36, increment=1, textvariable=self.horizon_var, width=8)
            self.horizon_spin.grid(row=0, column=3, padx=4, pady=6)

            # baseline
            try:
                baseline = self.data.groupby(self.data['date_achat'].dt.to_period("M"))['montant_total'].sum().mean()
            except Exception:
                baseline = 100000.0
            ttk.Label(self.form_frame, text=f"Baseline mensuel (historique): {baseline:,.0f} FCFA").grid(row=1, column=0, columnspan=4, sticky="w", padx=4, pady=(6,0))

        else:  # comportementale
            ttk.Label(self.form_frame, text="Type de promo:").grid(row=0, column=0, sticky="w", padx=4, pady=6)
            self.promo_var = tk.StringVar(value="coupon")
            self.promo_combo = ttk.Combobox(self.form_frame, textvariable=self.promo_var, values=["coupon", "points_fidelite", "reduction"], state="readonly", width=18)
            self.promo_combo.grid(row=0, column=1, padx=4, pady=6)

            ttk.Label(self.form_frame, text="% Clients ciblés:").grid(row=0, column=2, sticky="w", padx=4, pady=6)
            self.target_pct_var = tk.DoubleVar(value=10.0)
            self.target_pct_spin = ttk.Spinbox(self.form_frame, from_=1, to=100, increment=1, textvariable=self.target_pct_var, width=12)
            self.target_pct_spin.grid(row=0, column=3, padx=4, pady=6)

            ttk.Label(self.form_frame, text="Durée promo (jours):").grid(row=1, column=0, sticky="w", padx=4, pady=6)
            self.duree_var = tk.IntVar(value=7)
            self.duree_spin = ttk.Spinbox(self.form_frame, from_=1, to=365, increment=1, textvariable=self.duree_var, width=12)
            self.duree_spin.grid(row=1, column=1, padx=4, pady=6)

            ttk.Label(self.form_frame, text="(Les comportements sont modélisés à partir de segments RFM)").grid(row=2, column=0, columnspan=4, sticky="w", padx=4, pady=(6,0))

        # clear KPI area when changing form
        for w in self.kpi_frame.winfo_children():
            w.destroy()
        self.update_display()

    # ---------------- Run / delegate ----------------
    def _run_simulation(self):
        t = self.current_type.get()
        if t == "marketing":
            self._run_marketing()
        elif t == "statistique":
            self._run_statistique()
        else:
            self._run_comportementale()
        self.update_display()

    # --- Marketing simulation ---
    def _run_marketing(self):
        try:
            remise = float(self.remise_var.get())
            cout = float(self.cout_var.get())
            clients = int(self.clients_var.get())
            qty = int(self.qty_var.get())
        except Exception as e:
            self._show_error(f"Paramètres marketing invalides: {e}")
            return

        try:
            prix_moyen = float(self.data['prix_unitaire'].mean())
        except Exception:
            prix_moyen = 1000.0

        taux_conversion = min(0.02 + remise / 250.0, 0.9)
        clients_gagnes = int(clients * taux_conversion)

        revenu_brut = prix_moyen * qty * clients_gagnes
        reduction = revenu_brut * (remise / 100.0)
        revenu_net = revenu_brut - reduction
        benefice = revenu_net - cout
        roi = (benefice / cout * 100.0) if cout != 0 else None

        sim = {
            "% Remise": remise,
            "Coût campagne": round(cout, 2),
            "Clients ciblés": clients,
            "Clients gagnés": clients_gagnes,
            "Quantité moyenne": qty,
            "Revenu brut": round(revenu_brut, 2),
            "Réduction totale": round(reduction, 2),
            "Revenu net": round(revenu_net, 2),
            "Bénéfice": round(benefice, 2),
            "ROI (%)": round(roi, 2) if roi is not None else None
        }

        key = "sim_results_marketing"
        if shared_data[key].empty:
            shared_data[key] = pd.DataFrame([sim])
        else:
            shared_data[key] = pd.concat([shared_data[key], pd.DataFrame([sim])], ignore_index=True)

        # show KPIs
        self._show_kpis_from_dict({
            "Revenu net": format_fcfa(sim["Revenu net"]),
            "Bénéfice": format_fcfa(sim["Bénéfice"]),
            "ROI (%)": f"{sim['ROI (%)']} %" if sim['ROI (%)'] is not None else "N/A",
            "Clients gagnés": sim["Clients gagnés"]
        })

    # --- Statistique simulation ---
    def _run_statistique(self):
        try:
            growth = float(self.growth_var.get()) / 100.0
            horizon = int(self.horizon_var.get())
        except Exception as e:
            self._show_error(f"Paramètres statistiques invalides: {e}")
            return

        try:
            monthly = self.data.groupby(self.data['date_achat'].dt.to_period("M"))['montant_total'].sum()
            baseline = monthly.mean() if not monthly.empty else 100000.0
        except Exception:
            baseline = 100000.0

        projections = []
        for m in range(1, horizon + 1):
            projected = baseline * ((1 + growth) ** m)
            projections.append(round(projected, 2))

        sim = {
            "Croissance mensuelle (%)": round(growth * 100, 2),
            "Horizon (mois)": horizon,
            "Baseline mensuel": round(baseline, 2),
            "Projection finale": round(projections[-1], 2)
        }

        key = "sim_results_statistique"
        if shared_data[key].empty:
            shared_data[key] = pd.DataFrame([sim])
        else:
            shared_data[key] = pd.concat([shared_data[key], pd.DataFrame([sim])], ignore_index=True)

        self._show_kpis_from_dict({
            "Baseline mensuel": format_fcfa(sim["Baseline mensuel"]),
            f"Projection {horizon}m": format_fcfa(sim["Projection finale"]),
            "Croissance/m": f"{sim['Croissance mensuelle (%)']} %"
        })

    # --- Comportementale simulation ---
    def _run_comportementale(self):
        try:
            promo = self.promo_var.get()
            target_pct = float(self.target_pct_var.get()) / 100.0
            duree = int(self.duree_var.get())
        except Exception as e:
            self._show_error(f"Paramètres comportementaux invalides: {e}")
            return

        baseline_clients = len(self.data['client_id'].unique()) if 'client_id' in self.data else 1000
        cible = int(baseline_clients * target_pct)

        effectiveness = {"coupon": 0.25, "reduction": 0.18, "points_fidelite": 0.12}
        taux_reponse = effectiveness.get(promo, 0.12)
        clients_repondants = int(cible * taux_reponse)

        churn_avert = round(clients_repondants * 0.02 * (duree / 30.0), 2)
        fidel_gain = round(clients_repondants * 0.1, 2)

        sim = {
            "Type promo": promo,
            "Clients ciblés": cible,
            "Clients répondants": clients_repondants,
            "Churn évité (est.)": churn_avert,
            "Fidélisation gain (est.)": fidel_gain,
            "Durée (jours)": duree
        }

        key = "sim_results_comportementale"
        if shared_data[key].empty:
            shared_data[key] = pd.DataFrame([sim])
        else:
            shared_data[key] = pd.concat([shared_data[key], pd.DataFrame([sim])], ignore_index=True)

        self._show_kpis_from_dict({
            "Clients répondants": sim["Clients répondants"],
            "Churn évité": sim["Churn évité (est.)"],
            "Fidélisation": sim["Fidélisation gain (est.)"]
        })

    # ---------------- Helpers: KPI and errors ----------------
    def _show_kpis_from_dict(self, d: dict):
        for w in self.kpi_frame.winfo_children():
            w.destroy()
        for i, (k, v) in enumerate(d.items()):
            frm = tk.Frame(self.kpi_frame, bg=KPI_BG, width=180, height=70)
            frm.pack_propagate(False)
            frm.grid(row=0, column=i, padx=8, pady=4, sticky="nsew")
            lbl_title = tk.Label(frm, text=k, fg="white", bg=KPI_BG, font=("Segoe UI", 9, "bold"))
            lbl_title.pack(anchor="n", pady=(6,0))
            lbl_val = tk.Label(frm, text=str(v), fg=KPI_FG, bg=KPI_BG, font=("Segoe UI", 11, "bold"))
            lbl_val.pack(anchor="n", pady=(0,6))

    def _show_error(self, msg):
        for w in self.kpi_frame.winfo_children():
            w.destroy()
        ttk.Label(self.kpi_frame, text=msg, foreground="red").pack()

    # ---------------- Graphs & Table display ----------------
    def update_display(self):
        t = self.current_type.get()
        self._render_graphs_for_type(t)
        self._render_table_for_type(t)

    def _render_graphs_for_type(self, t):
        for w in self.graph_frame.winfo_children():
            w.destroy()
        key = f"sim_results_{t}"
        df = shared_data.get(key, pd.DataFrame())
        fig_size = (4.5, 3.2)
        figs = []

        if t == "marketing":
            if df.empty:
                ttk.Label(self.graph_frame, text="Aucune simulation marketing enregistrée").grid(row=0, column=0, padx=10, pady=10)
                return
            fig1, ax1 = plt.subplots(figsize=fig_size)
            ax1.bar(df["% Remise"].astype(str), df["Revenu net"], color="skyblue")
            ax1.set_title("Revenu net par % remise")
            ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " ")))
            ax1.tick_params(axis='x', rotation=30, labelsize=8)
            mplcursors.cursor(ax1.containers, hover=True)
            figs.append((fig1, 0, 0))

            fig2, ax2 = plt.subplots(figsize=fig_size)
            ax2.plot(df["% Remise"], df["ROI (%)"], marker="o", color="green")
            ax2.set_title("ROI (%) selon % remise")
            ax2.set_xlabel("% Remise")
            ax2.set_ylabel("ROI (%)")
            mplcursors.cursor(ax2.lines, hover=True)
            figs.append((fig2, 0, 1))

            fig3, ax3 = plt.subplots(figsize=fig_size)
            ax3.bar(df["% Remise"].astype(str), df["Clients ciblés"], alpha=0.5, label="Ciblés")
            ax3.bar(df["% Remise"].astype(str), df["Clients gagnés"], alpha=0.8, label="Gagnés")
            ax3.set_title("Clients ciblés vs gagnés")
            ax3.legend()
            ax3.tick_params(axis='x', rotation=30, labelsize=8)
            mplcursors.cursor(ax3.containers, hover=True)
            figs.append((fig3, 1, 0))

            fig4, ax4 = plt.subplots(figsize=fig_size)
            ax4.scatter(df["Coût campagne"], df["Bénéfice"], c="red")
            ax4.set_title("Bénéfice net selon coût campagne")
            ax4.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " ")))
            ax4.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " ")))
            mplcursors.cursor(ax4.collections, hover=True)
            figs.append((fig4, 1, 1))

        elif t == "statistique":
            if df.empty:
                ttk.Label(self.graph_frame, text="Aucune simulation statistique enregistrée").grid(row=0, column=0, padx=10, pady=10)
                return
            fig1, ax1 = plt.subplots(figsize=fig_size)
            ax1.scatter(df["Croissance mensuelle (%)"], df["Projection finale"], c="blue")
            ax1.set_title("Projection finale vs croissance mensuelle")
            ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " ")))
            mplcursors.cursor(ax1.collections, hover=True)
            figs.append((fig1, 0, 0))

            fig2, ax2 = plt.subplots(figsize=fig_size)
            ax2.hist(df["Baseline mensuel"].astype(float), bins=8, color="purple", edgecolor="black")
            ax2.set_title("Distribution Baseline mensuel")
            mplcursors.cursor(ax2.patches, hover=True)
            figs.append((fig2, 0, 1))

            fig3, ax3 = plt.subplots(figsize=fig_size)
            ax3.plot(df["Horizon (mois)"], df["Projection finale"], marker="o")
            ax3.set_title("Projection finale selon horizon")
            ax3.set_xlabel("Horizon (mois)")
            mplcursors.cursor(ax3.lines, hover=True)
            figs.append((fig3, 1, 0))

            fig4, ax4 = plt.subplots(figsize=fig_size)
            ax4.bar(df["Croissance mensuelle (%)"].astype(str), df["Projection finale"], color="orange")
            ax4.set_title("Projection par taux de croissance")
            ax4.tick_params(axis='x', rotation=30, labelsize=8)
            mplcursors.cursor(ax4.containers, hover=True)
            figs.append((fig4, 1, 1))

        else:  # comportementale
            if df.empty:
                ttk.Label(self.graph_frame, text="Aucune simulation comportementale enregistrée").grid(row=0, column=0, padx=10, pady=10)
                return
            fig1, ax1 = plt.subplots(figsize=fig_size)
            try:
                agg = df.groupby("Type promo")["Clients répondants"].sum()
                ax1.bar(agg.index.astype(str), agg.values, color="teal")
            except Exception:
                ax1.text(0.5, 0.5, "Données insuffisantes", ha="center")
            ax1.set_title("Clients répondants par type promo")
            mplcursors.cursor(ax1.containers, hover=True)
            figs.append((fig1, 0, 0))

            fig2, ax2 = plt.subplots(figsize=fig_size)
            try:
                agg2 = df.groupby("Type promo")["Churn évité (est.)"].sum()
                ax2.bar(agg2.index.astype(str), agg2.values, color="coral")
            except Exception:
                ax2.text(0.5, 0.5, "Données insuffisantes", ha="center")
            ax2.set_title("Churn évité par type promo")
            mplcursors.cursor(ax2.containers, hover=True)
            figs.append((fig2, 0, 1))

            fig3, ax3 = plt.subplots(figsize=fig_size)
            ax3.bar(df.index.astype(str), df["Clients ciblés"], alpha=0.5, label="Ciblés")
            ax3.bar(df.index.astype(str), df["Clients répondants"], alpha=0.8, label="Répondants")
            ax3.set_title("Ciblés vs répondants (historique sims)")
            ax3.legend()
            mplcursors.cursor(ax3.containers, hover=True)
            figs.append((fig3, 1, 0))

            fig4, ax4 = plt.subplots(figsize=fig_size)
            ax4.scatter(df["Durée (jours)"], df["Fidélisation gain (est.)"], c="purple")
            ax4.set_title("Durée promo vs fidélisation estimée")
            mplcursors.cursor(ax4.collections, hover=True)
            figs.append((fig4, 1, 1))

        # Place figures, ensure margins safe
        for fig, r, c in figs:
            fig.tight_layout()
            plt.subplots_adjust(top=0.88, bottom=0.12, left=0.12, right=0.95)
            canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
            canvas.draw()
            widget = canvas.get_tk_widget()
            widget.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")

    def _render_table_for_type(self, t):
        for w in self.table_frame.winfo_children():
            w.destroy()
        key = f"sim_results_{t}"
        df = shared_data.get(key, pd.DataFrame())
        cols = list(df.columns) if not df.empty else ["Aucune donnée"]
        tree = ttk.Treeview(self.table_frame, columns=cols, show="headings")
        vsb = ttk.Scrollbar(self.table_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(self.table_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.table_frame.rowconfigure(0, weight=1)
        self.table_frame.columnconfigure(0, weight=1)

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=140, anchor="center")

        tree.tag_configure('odd', background='#ffffff')
        tree.tag_configure('even', background='#f2f2f2')

        if not df.empty:
            for i, (_, row) in enumerate(df.iterrows()):
                vals = [row[c] for c in cols]
                tag = 'even' if i % 2 == 0 else 'odd'
                tree.insert("", "end", values=vals, tags=(tag,))

        self.tree = tree

    # ---------------- Scenarios ----------------
    def _open_scenario_dialog(self):
        t = self.current_type.get()
        # Predefined scenarios mapping
        scenarios = {
            "marketing": [
                {"label": "Promo légère", "params": {"remise": 10.0, "cout": 100000.0, "clients": 1000, "qty": 1}},
                {"label": "Promo agressive", "params": {"remise": 30.0, "cout": 300000.0, "clients": 5000, "qty": 1}}
            ],
            "statistique": [
                {"label": "Lente croissance", "params": {"growth": 2.0, "horizon": 6}},
                {"label": "Forte croissance", "params": {"growth": 5.0, "horizon": 12}}
            ],
            "comportementale": [
                {"label": "Coupon court", "params": {"promo": "coupon", "target_pct": 20.0, "duree": 30}},
                {"label": "Points long", "params": {"promo": "points_fidelite", "target_pct": 50.0, "duree": 90}}
            ]
        }
        choices = scenarios.get(t, [])
        if not choices:
            self._show_error("Aucun scénario prédéfini pour ce type.")
            return

        # Simple selection dialog
        labels = [s["label"] for s in choices]
        sel = simpledialog.askstring("Scénarios prédéfinis", "Choisir scénario:\n" + "\n".join(f"{i+1}. {lab}" for i, lab in enumerate(labels)))
        if not sel:
            return
        # allow numeric index or label
        sel = sel.strip()
        try:
            idx = int(sel) - 1
            scenario = choices[idx]
        except Exception:
            # match label
            scenario = next((s for s in choices if s["label"].lower() == sel.lower()), None)
        if not scenario:
            self._show_error("Scénario non reconnu.")
            return

        # apply chosen scenario
        params = scenario["params"]
        if t == "marketing":
            self.remise_var.set(params.get("remise", 10.0))
            self.cout_var.set(params.get("cout", 50000.0))
            self.clients_var.set(params.get("clients", 1000))
            self.qty_var.set(params.get("qty", 1))
        elif t == "statistique":
            self.growth_var.set(params.get("growth", 2.0))
            self.horizon_var.set(params.get("horizon", 6))
        else:
            self.promo_var.set(params.get("promo", "coupon"))
            self.target_pct_var.set(params.get("target_pct", 10.0))
            self.duree_var.set(params.get("duree", 7))
        # run immediately for demo convenience
        self._run_simulation()

    # ---------------- Utilities: clear / sort ----------------
    def _clear_current(self):
        t = self.current_type.get()
        key = f"sim_results_{t}"
        shared_data[key] = pd.DataFrame()
        self.update_display()
        ttk.Label(self.kpi_frame, text="Historique effacé.", foreground="orange").pack()

    def sort_column(self, col):
        t = self.current_type.get()
        key = f"sim_results_{t}"
        df = shared_data.get(key, pd.DataFrame())
        if df.empty or col not in df.columns:
            return
        rev = self.sort_directions.get(col, False)
        try:
            df_sorted = df.sort_values(by=col, ascending=not rev)
        except Exception:
            df_sorted = df
        self.sort_directions[col] = not rev
        shared_data[key] = df_sorted.reset_index(drop=True)
        self._render_table_for_type(t)
