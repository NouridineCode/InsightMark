# onglets/forecast_page.py
import tkinter as tk
from tkinter import ttk
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import mplcursors
from sklearn.linear_model import LinearRegression

from data_loader import load_data
from shared_data import shared_data

# === Design constants ===
PRIMARY_BTN_BG = "#00cec9"
PRIMARY_BTN_FG = "black"
KPI_BG = "#2c2c3c"
KPI_TITLE_FG = "white"
KPI_VALUE_FG = "#00cec9"

def fmt_fcfa_val(x):
    """Formatage FCFA sans notation scientifique."""
    try:
        return f"{int(round(x)):,}".replace(",", " ")
    except Exception:
        return str(x)

def safe_import_ses():
    try:
        from statsmodels.tsa.holtwinters import SimpleExpSmoothing
        return SimpleExpSmoothing
    except Exception:
        return None


class ForecastPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.data = load_data()
        self.SES = safe_import_ses()
        self.model_choice = tk.StringVar(value="auto")  # auto / linreg / ses
        self._build_ui()

    def _build_ui(self):
        # === Controls ===
        controls = ttk.Frame(self)
        controls.pack(fill="x", padx=12, pady=10)

        ttk.Label(controls, text="Nombre de mois à prédire :").pack(side="left")
        self.nb_mois_var = tk.IntVar(value=6)
        spin = ttk.Spinbox(controls, from_=1, to=24, textvariable=self.nb_mois_var, width=5)
        spin.pack(side="left", padx=5)

        run_btn = tk.Button(
            controls, text="Lancer la prévision",
            bg=PRIMARY_BTN_BG, fg=PRIMARY_BTN_FG,
            font=("Segoe UI", 10, "bold"), bd=0, padx=10, pady=6,
            command=self.lancer_prevision
        )
        run_btn.pack(side="left", padx=6)

        # === Model choice toggle ===
        model_frame = ttk.LabelFrame(controls, text="Modèle")
        model_frame.pack(side="left", padx=15)

        for text, val in [("Auto", "auto"), ("Régression", "linreg"), ("SES", "ses")]:
            ttk.Radiobutton(model_frame, text=text, value=val, variable=self.model_choice).pack(side="left", padx=5)

        # === Notebook ===
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_main = ttk.Frame(self.notebook)
        self.tab_table = ttk.Frame(self.notebook)
        self.tab_advanced = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_main, text="Vue d'ensemble")
        self.notebook.add(self.tab_table, text="Tableau")
        self.notebook.add(self.tab_advanced, text="Avancé")

    def lancer_prevision(self):
        # Reset tabs
        for frame in (self.tab_main, self.tab_table, self.tab_advanced):
            for w in frame.winfo_children():
                w.destroy()

        if "date_achat" not in self.data.columns or "montant_total" not in self.data.columns:
            ttk.Label(self.tab_main, text="Colonnes manquantes.", foreground="red").pack()
            return

        df = self.data.copy()
        df["date_achat"] = pd.to_datetime(df["date_achat"], errors="coerce")
        monthly = df.groupby(df["date_achat"].dt.to_period("M")).agg({"montant_total": "sum"})
        monthly.index = monthly.index.to_timestamp()
        monthly = monthly.reset_index().rename(columns={"date_achat": "date", "montant_total": "montant"})

        if monthly.empty:
            ttk.Label(self.tab_main, text="Aucune donnée.", foreground="red").pack()
            return

        # Data
        nb_mois = int(self.nb_mois_var.get())
        last_date = monthly["date"].iloc[-1]
        future_dates = pd.date_range(last_date + pd.DateOffset(months=1), periods=nb_mois, freq="MS")

        # LinReg
        monthly["mois_int"] = np.arange(len(monthly))
        X, y = monthly[["mois_int"]].values, monthly["montant"].values
        lin_model = LinearRegression().fit(X, y)
        lin_future = lin_model.predict(np.arange(len(monthly), len(monthly)+nb_mois).reshape(-1, 1))

        # SES
        ses_future = None
        if self.SES:
            try:
                ses_model = self.SES(monthly["montant"]).fit(smoothing_level=0.6, optimized=False)
                ses_future = ses_model.forecast(nb_mois).values
            except Exception:
                pass

        # Choix modèle
        chosen = self.model_choice.get()
        if chosen == "linreg":
            model_name, preds = "Régression linéaire", lin_future
        elif chosen == "ses" and ses_future is not None:
            model_name, preds = "SES", ses_future
        else:  # auto
            lin_err = np.mean(np.abs(y - lin_model.predict(X)))
            ses_err = np.mean(np.abs(y - ses_model.fittedvalues)) if ses_future is not None else np.inf
            if ses_err < lin_err:
                model_name, preds = "SES", ses_future
            else:
                model_name, preds = "Régression linéaire", lin_future

        # DF final
        forecast_df = pd.DataFrame({
            "date": pd.concat([monthly["date"], pd.Series(future_dates)]).reset_index(drop=True),
            "montant": pd.concat([monthly["montant"], pd.Series(preds)]).reset_index(drop=True),
            "type": ["historique"]*len(monthly) + ["prévu"]*nb_mois
        })
        shared_data["forecasts"] = forecast_df.copy()

        # === KPI Cards ===
        future_df = forecast_df[forecast_df["type"] == "prévu"]
        moyenne = round(future_df["montant"].mean(), 2)
        maximum = round(future_df["montant"].max(), 2)
        tendance = "📈 Croissante" if future_df["montant"].iloc[-1] > future_df["montant"].iloc[0] else "📉 Décroissante"

        kpi_frame = tk.Frame(self.tab_main, bg=self.master["bg"])
        kpi_frame.pack(fill="x", padx=10, pady=8)
        kpi_frame.columnconfigure((0,1,2,3), weight=1)

        def kpi_card(title, val, col):
            card = tk.Frame(kpi_frame, bg=KPI_BG, width=220, height=70)
            card.pack_propagate(False)
            card.grid(row=0, column=col, padx=8, pady=4, sticky="nsew")
            tk.Label(card, text=title, bg=KPI_BG, fg=KPI_TITLE_FG).pack(anchor="n", pady=(8,0))
            tk.Label(card, text=val, bg=KPI_BG, fg=KPI_VALUE_FG, font=("Segoe UI", 11, "bold")).pack(anchor="n")
        kpi_card("Moyenne", fmt_fcfa_val(moyenne), 0)
        kpi_card("Maximum", fmt_fcfa_val(maximum), 1)
        kpi_card("Tendance", tendance, 2)
        kpi_card("Modèle", model_name, 3)

        # === Graphiques (2 colonnes) ===
        figs = []  # 🔹 liste de figures

        graph_frame = ttk.Frame(self.tab_main)
        graph_frame.pack(fill="both", expand=True, padx=8, pady=8)
        graph_frame.columnconfigure((0,1), weight=1)

        # Historique vs Prévision
        fig1, ax1 = plt.subplots(figsize=(5.8,3.6))
        for typ, g in forecast_df.groupby("type"):
            style = "--" if typ=="prévu" else "-"
            color = "#00cec9" if typ=="prévu" else "#2c3e50"
            ax1.plot(g["date"], g["montant"], label=typ, marker="o", color=color, linestyle=style)
        ax1.set_title("Historique vs Prévision")
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=6))
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax1.tick_params(axis="x", rotation=30, labelsize=8)
        ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: fmt_fcfa_val(x)))
        ax1.legend()
        mplcursors.cursor(ax1.lines, hover=True).connect("add", 
            lambda sel: sel.annotation.set_text(f"{mdates.num2date(sel.target[0]).strftime('%Y-%m')}\n{fmt_fcfa_val(sel.target[1])}")
        )
        FigureCanvasTkAgg(fig1, master=graph_frame).get_tk_widget().grid(row=0,column=0,sticky="nsew")
        figs.append(fig1)

        # Prévisions mensuelles
        fig2, ax2 = plt.subplots(figsize=(5.8,3.6))
        bars = ax2.bar(future_df["date"].dt.strftime("%Y-%m"), future_df["montant"], color="#00cec9")
        ax2.set_title("Prévisions mensuelles")
        ax2.tick_params(axis="x", rotation=30, labelsize=8)
        ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: fmt_fcfa_val(x)))
        mplcursors.cursor(bars, hover=True).connect("add", 
            lambda sel: sel.annotation.set_text(fmt_fcfa_val(sel.artist.datavalues[sel.index]))
        )
        FigureCanvasTkAgg(fig2, master=graph_frame).get_tk_widget().grid(row=0,column=1,sticky="nsew")
        figs.append(fig2)

        # === Tableau ===
        vsb = ttk.Scrollbar(self.tab_table, orient="vertical")
        vsb.pack(side="right", fill="y")
        tree = ttk.Treeview(self.tab_table, columns=("Mois","Montant","Type"), show="headings", yscrollcommand=vsb.set)
        for col in ("Mois","Montant","Type"):
            tree.heading(col,text=col)
        tree.pack(fill="both", expand=True)
        vsb.config(command=tree.yview)
        for _,r in forecast_df.iterrows():
            tree.insert("", "end", values=(r["date"].strftime("%Y-%m"), fmt_fcfa_val(r["montant"]), r["type"]))

        # === Avancé : Courbe de Lorenz ===
        if "client_id" in self.data.columns:
            clients = self.data.groupby("client_id")["montant_total"].sum().sort_values(ascending=False)
            if not clients.empty:
                cum = clients.cumsum()/clients.sum()
                share = np.arange(1,len(clients)+1)/len(clients)
                figL, axL = plt.subplots(figsize=(6,4))
                axL.plot(share,cum,label="Lorenz",color="#2c3e50")
                axL.plot([0,1],[0,1],"--",color="gray")
                axL.set_title("Courbe de Lorenz – 20/80")
                axL.yaxis.set_major_formatter(mticker.PercentFormatter(1))
                mplcursors.cursor(axL.lines,hover=True).connect("add", 
                    lambda sel: sel.annotation.set_text(f"{sel.target[1]*100:.1f}%")
                )
                FigureCanvasTkAgg(figL, master=self.tab_advanced).get_tk_widget().pack(fill="both", expand=True)
                figs.append(figL)

        # 🔹 Sauvegarde globale pour export
        shared_data["figs"] = figs
        shared_data["forecasts"] = forecast_df.copy()
