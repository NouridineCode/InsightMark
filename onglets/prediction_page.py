import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
import pandas as pd
import numpy as np
from data_loader import load_data
from shared_data import shared_data

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_curve, auc,
    precision_score, recall_score, accuracy_score
)

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
import mplcursors


PRIMARY_BTN_BG = "#00cec9"
PRIMARY_BTN_FG = "black"
KPI_BG = "#2c2c3c"
KPI_TITLE_FG = "white"
KPI_VALUE_FG = "#00cec9"


def _safe_draw(canvas: FigureCanvasTkAgg, fig: plt.Figure, left: float = 0.1):
    try:
        fig.tight_layout(rect=[0, 0, 1, 0.95])
    except Exception:
        pass
    fig.subplots_adjust(left=left, right=0.96, top=0.9, bottom=0.15)
    canvas.draw()


class PredictionPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.raw = load_data()
        self._diagnostic_data()

        if self.raw is None or self.raw.empty:
            ttk.Label(self, text="Aucune donnée disponible.", font=("Segoe UI", 14)).pack(pady=20)
            return

        self._try_load_xgb()
        self._build_ui()

    def _diagnostic_data(self):
        print("=== Diagnostic données chargées (PredictionPage) ===")
        if self.raw is None:
            print("Erreur : self.raw est None")
        elif self.raw.empty:
            print("Erreur : self.raw est un DataFrame vide")
        else:
            print(f"Colonnes disponibles : {list(self.raw.columns)}")
            print("Aperçu des 5 premières lignes :")
            print(self.raw.head())

    def _try_load_xgb(self):
        try:
            from xgboost import XGBClassifier  # type: ignore
            self.XGBAvailable = True
            self.XGBClass = XGBClassifier
        except Exception:
            self.XGBAvailable = False
            self.XGBClass = None

    def _build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=6)
        ttk.Label(header, text="Prédiction du risque de désabonnement",
                  font=("Segoe UI", 14, "bold")).pack(side="left")

        controls = ttk.Frame(self)
        controls.pack(fill="x", padx=10, pady=(0, 8))
        ttk.Label(controls, text="Modèle :").pack(side="left", padx=(6, 4))
        self.model_choice = tk.StringVar(value="logreg")
        options = [("Régression logistique", "logreg"),
                   ("Forêt aléatoire", "rf"),
                   ("SVM (prob)", "svm")]
        for text, val in options:
            ttk.Radiobutton(controls, text=text, value=val, variable=self.model_choice).pack(side="left", padx=4)
        if self.XGBAvailable:
            ttk.Radiobutton(controls, text="XGBoost", value="xgb", variable=self.model_choice).pack(side="left", padx=4)

        run_btn = tk.Button(controls, text="Lancer la prédiction", bg=PRIMARY_BTN_BG, fg=PRIMARY_BTN_FG,
                            font=("Segoe UI", 10, "bold"), bd=0, padx=10, pady=6, command=self.run_prediction)
        run_btn.pack(side="left", padx=10)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_report = ttk.Frame(self.notebook)
        self.tab_graphs = ttk.Frame(self.notebook)
        self.tab_top10 = ttk.Frame(self.notebook)  # Onglet Top 10 séparé

        self.notebook.add(self.tab_report, text="Rapport")
        self.notebook.add(self.tab_graphs, text="Graphiques")
        self.notebook.add(self.tab_top10, text="Top 10 clients à risque")

        self.kpi_frame = tk.Frame(self.tab_report)
        self.kpi_frame.pack(fill="x", pady=8)
        self.report_table = ttk.Treeview(self.tab_report, show="headings", height=6)
        self.report_table.pack(fill="both", expand=True, padx=10, pady=8)

        self.graphs_frame = ttk.Frame(self.tab_graphs)
        self.graphs_frame.pack(fill="both", expand=True)

        self.top10_frame = ttk.Frame(self.tab_top10)
        self.top10_frame.pack(fill="both", expand=True)

    def _prepare_dataset(self):
        df = self.raw.copy()
        if "client_id" in df.columns:
            if "date_achat" in df.columns:
                df["date_achat"] = pd.to_datetime(df["date_achat"], errors="coerce")

            aggs = {"montant_total": "sum", "achat_id": "nunique"}
            if "note_satisfaction" in df.columns:
                aggs["note_satisfaction"] = "mean"
            client_df = df.groupby("client_id").agg(aggs).rename(
                columns={"achat_id": "nb_achats", "note_satisfaction": "note_satisfaction_mean"}
            ).reset_index()

            if "date_achat" in df.columns:
                last_dates = df.groupby("client_id")["date_achat"].max().rename("last_purchase")
                client_df = client_df.merge(last_dates.reset_index(), on="client_id", how="left")
        else:
            client_df = df.copy()

        if "desabonnement" in client_df.columns:
            client_df["desabonnement"] = client_df["desabonnement"].astype(int)
        else:
            if "last_purchase" in client_df.columns:
                overall_last = self.raw["date_achat"].dropna().max() if "date_achat" in self.raw.columns else pd.Timestamp.now()
                threshold = overall_last - pd.DateOffset(months=12)
                client_df["desabonnement"] = (
                    (client_df["last_purchase"].isna()) | (client_df["last_purchase"] < threshold)
                ).astype(int)
            else:
                client_df["desabonnement"] = (client_df.get("nb_achats", 0) <= 1).astype(int)

        features = [c for c in ["montant_total", "nb_achats", "note_satisfaction_mean"] if c in client_df.columns]
        client_df[features] = client_df[features].fillna(0)
        client_df = client_df.set_index("client_id", drop=False)

        print("=== Dataset client préparé ===")
        print(client_df.head())
        print(f"Features utilisées : {features}")

        return client_df, features

    def _make_model(self):
        choice = self.model_choice.get()
        if choice == "logreg":
            return Pipeline([("scaler", StandardScaler()), ("model", LogisticRegression(max_iter=2000))])
        elif choice == "rf":
            return Pipeline([("model", RandomForestClassifier(n_estimators=200, random_state=42))])
        elif choice == "svm":
            return Pipeline([("scaler", StandardScaler()), ("model", SVC(probability=True))])
        elif choice == "xgb" and self.XGBAvailable:
            return Pipeline([("model", self.XGBClass(use_label_encoder=False, eval_metric="logloss"))])
        else:
            return Pipeline([("scaler", StandardScaler()), ("model", LogisticRegression(max_iter=2000))])

    def run_prediction(self):
        # Nettoyage des frames
        for w in self.kpi_frame.winfo_children(): w.destroy()
        for w in self.graphs_frame.winfo_children(): w.destroy()
        for w in self.top10_frame.winfo_children(): w.destroy()
        self.report_table.delete(*self.report_table.get_children())

        try:
            client_df, features = self._prepare_dataset()
        except Exception as e:
            messagebox.showerror("Erreur", f"Préparation impossible : {e}")
            return

        if client_df.empty or not features:
            messagebox.showerror("Erreur", "Données insuffisantes pour exécuter la prédiction.")
            return

        X = client_df[features].values
        y = client_df["desabonnement"].values

        try:
            X_train, X_test, idx_train, idx_test = train_test_split(
                X, client_df.index.values, test_size=0.3, random_state=42,
                stratify=y if len(np.unique(y)) > 1 else None
            )
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du découpage train/test : {e}")
            return

        y_series = pd.Series(y, index=client_df.index)
        X_df = pd.DataFrame(X, index=client_df.index, columns=features)
        X_train_df, X_test_df = X_df.loc[idx_train], X_df.loc[idx_test]
        y_train, y_test = y_series.loc[idx_train], y_series.loc[idx_test]

        model = self._make_model()
        try:
            model.fit(X_train_df, y_train)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur à l'entraînement du modèle : {e}")
            return

        try:
            y_pred = model.predict(X_test_df)
            y_proba = model.predict_proba(X_test_df)[:, 1] if hasattr(model, "predict_proba") else y_pred
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors des prédictions : {e}")
            return

        acc_test = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        try:
            fpr_tmp, tpr_tmp, _ = roc_curve(y_test, y_proba)
            auc_score = auc(fpr_tmp, tpr_tmp)
        except Exception:
            auc_score = 0.0

        def kpi_card(title, val, col):
            card = tk.Frame(self.kpi_frame, bg=KPI_BG, width=180, height=70)
            card.pack_propagate(False)
            card.grid(row=0, column=col, padx=6, pady=4, sticky="nsew")
            tk.Label(card, text=title, bg=KPI_BG, fg=KPI_TITLE_FG).pack(anchor="n", pady=(8, 0))
            tk.Label(card, text=val, bg=KPI_BG, fg=KPI_VALUE_FG,
                     font=("Segoe UI", 11, "bold")).pack(anchor="n")

        kpi_card("Accuracy", f"{acc_test:.3f}", 0)
        kpi_card("Précision", f"{prec:.3f}", 1)
        kpi_card("Recall", f"{rec:.3f}", 2)
        kpi_card("AUC", f"{auc_score:.3f}", 3)

        report_dict = classification_report(y_test, y_pred, zero_division=0, output_dict=True)
        cols = ["Classe", "Precision", "Recall", "F1-score", "Support"]
        self.report_table["columns"] = cols
        for c in cols:
            self.report_table.heading(c, text=c)
            self.report_table.column(c, anchor="center", width=100)
        for label, vals in report_dict.items():
            if isinstance(vals, dict):
                self.report_table.insert("", "end", values=(
                    label, f"{vals['precision']:.2f}", f"{vals['recall']:.2f}",
                    f"{vals['f1-score']:.2f}", int(vals['support'])
                ))

        preds_df = X_test_df.copy()
        preds_df["client_id"] = preds_df.index  # ajoute client_id en tant que colonne
        preds_df["y_test"] = y_test
        preds_df["y_pred"] = y_pred
        preds_df["y_proba"] = y_proba

        figs = []

        self.graphs_frame.columnconfigure((0, 1), weight=1)
        self.graphs_frame.rowconfigure((0, 1), weight=1)

        # Matrice de confusion
        cm = confusion_matrix(y_test, y_pred)
        fig1, ax1 = plt.subplots(figsize=(4.5, 4))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax1,
                    xticklabels=["Non", "Oui"], yticklabels=["Non", "Oui"])
        ax1.set_title("Matrice de confusion")

        xmin, xmax = ax1.get_xlim()
        ymin, ymax = ax1.get_ylim()
        dx = (xmax - xmin) * 0.05
        dy = (ymax - ymin) * 0.05
        ax1.set_xlim(xmin - dx, xmax + dx)
        ax1.set_ylim(ymin - dy, ymax + dy)

        c1 = FigureCanvasTkAgg(fig1, master=self.graphs_frame)
        c1.get_tk_widget().grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        _safe_draw(c1, fig1)
        mplcursors.cursor(ax1.collections, hover=True)
        figs.append(fig1)

        # Courbe ROC
        fig2, ax2 = plt.subplots(figsize=(4.5, 4))
        fpr, tpr, _ = roc_curve(y_test, y_proba)
        l, = ax2.plot(fpr, tpr, label=f"AUC={auc_score:.2f}")
        ax2.plot([0, 1], [0, 1], "--", color="gray")
        ax2.set_title("Courbe ROC")

        xmin, xmax = ax2.get_xlim()
        ymin, ymax = ax2.get_ylim()
        dx = (xmax - xmin) * 0.05
        dy = (ymax - ymin) * 0.05
        ax2.set_xlim(xmin - dx, xmax + dx)
        ax2.set_ylim(ymin - dy, ymax + dy)

        ax2.legend()
        c2 = FigureCanvasTkAgg(fig2, master=self.graphs_frame)
        c2.get_tk_widget().grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        _safe_draw(c2, fig2)
        mplcursors.cursor([l], hover=True)
        figs.append(fig2)

        # Distribution des probabilités
        fig3, ax3 = plt.subplots(figsize=(4.5, 4))
        bars = sns.histplot(y_proba, bins=20, kde=True, ax=ax3)
        ax3.axvline(0.5, color="red", linestyle="--")
        ax3.set_title("Distribution des probabilités")

        xmin, xmax = ax3.get_xlim()
        ymin, ymax = ax3.get_ylim()
        dx = (xmax - xmin) * 0.05
        dy = (ymax - ymin) * 0.05
        ax3.set_xlim(xmin - dx, xmax + dx)
        ax3.set_ylim(ymin - dy, ymax + dy)

        c3 = FigureCanvasTkAgg(fig3, master=self.graphs_frame)
        c3.get_tk_widget().grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        _safe_draw(c3, fig3)
        mplcursors.cursor(bars.containers, hover=True)
        figs.append(fig3)

        # Importance des variables
        fig4, ax4 = plt.subplots(figsize=(4.5, 4))
        model_obj = model.named_steps.get("model", model)
        if hasattr(model_obj, "feature_importances_"):
            imp = pd.Series(model_obj.feature_importances_, index=features).sort_values()
            imp.plot.barh(ax=ax4, color="teal")
        elif hasattr(model_obj, "coef_"):
            coef = model_obj.coef_[0]
            imp = pd.Series(coef, index=features).sort_values(key=abs)
            ax4.barh(imp.index, imp.values,
                    color=["green" if v > 0 else "red" for v in imp.values])
        else:
            ax4.text(0.5, 0.5, "Pas d'importance dispo", ha="center")
        ax4.set_title("Importance des variables")

        xmin, xmax = ax4.get_xlim()
        ymin, ymax = ax4.get_ylim()
        dx = (xmax - xmin) * 0.05
        dy = (ymax - ymin) * 0.05
        ax4.set_xlim(xmin - dx, xmax + dx)
        ax4.set_ylim(ymin - dy, ymax + dy)

        c4 = FigureCanvasTkAgg(fig4, master=self.graphs_frame)
        c4.get_tk_widget().grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        _safe_draw(c4, fig4)
        mplcursors.cursor(ax4.patches, hover=True)
        figs.append(fig4)

        # Top 10 clients dans onglet dédié
        top10 = preds_df.sort_values("y_proba", ascending=False).head(10)
        ttk.Label(self.top10_frame, text="Top 10 clients à risque", font=("Segoe UI", 11, "bold")).pack(pady=6)

        cols = ["client_id"] + features + ["y_test", "y_pred", "y_proba"]
        tree = ttk.Treeview(self.top10_frame, columns=cols, show="headings", height=15)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=100, anchor="center")
        tree.pack(fill="both", expand=True, padx=10, pady=8)

        for _, row in top10.iterrows():
            tree.insert("", "end", values=[row[c] for c in cols])

        def on_double_click(event):
            item = tree.selection()
            if not item:
                return
            vals = tree.item(item[0], "values")
            cid = vals[0]
            self.show_client_detail(cid, client_df)

        tree.bind("<Double-1>", on_double_click)

        shared_data["predictions"] = preds_df.copy()
        shared_data["figs"] = figs

    def show_client_detail(self, client_id, client_df):
        popup = Toplevel(self)
        popup.title(f"Détails client {client_id}")
        popup.geometry("500x400")

        if client_id not in client_df.index:
            messagebox.showerror("Erreur", f"Client {client_id} non trouvé.")
            popup.destroy()
            return

        client_data = client_df.loc[client_id]
        text = tk.Text(popup, wrap="word")
        text.pack(fill="both", expand=True)
        text.insert(tk.END, f"=== Détails client {client_id} ===\n\n")
        for col, val in client_data.items():
            text.insert(tk.END, f"{col}: {val}\n")
        text.configure(state="disabled")
