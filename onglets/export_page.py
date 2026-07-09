import io
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
from shared_data import shared_data  # dictionnaire partagé

# ReportLab pour PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet


class ExportPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#f0f0f0")

        title = tk.Label(self, text="Export des Données et Graphiques",
                         font=("Arial", 16, "bold"), bg="#f0f0f0")
        title.pack(pady=20)

        # Liste déroulante pour choisir quoi exporter
        self.data_options = [
            ("Données brutes", "df"),
            ("Résultats RFM", "rfm_results"),
            ("Segmentation", "segment_df"),
            ("Prévisions", "forecasts"),
            ("Prédictions", "predictions"),
            ("Anomalies", "anomalies"),
            ("Simulation", "simulation_results"),
            ("Risque de désabonnement", "churn_risk"),
            ("IA", "ai_responses"),
            ("Filtres appliqués", "filters")
        ]

        tk.Label(self, text="Choisissez le jeu de données à exporter :", bg="#f0f0f0").pack(pady=10)
        self.selected_option = tk.StringVar()
        self.dropdown = ttk.Combobox(
            self,
            textvariable=self.selected_option,
            values=[opt[0] for opt in self.data_options],
            state="readonly",
            width=40
        )
        self.dropdown.pack(pady=5)

        # Choix du scope d'export (données / graphiques / les deux)
        scope_frame = tk.Frame(self, bg="#f0f0f0")
        scope_frame.pack(pady=8)
        self.export_scope = tk.StringVar(value="both")
        tk.Radiobutton(scope_frame, text="Données + Graphiques", variable=self.export_scope, value="both",
                       bg="#f0f0f0").grid(row=0, column=0, padx=8)
        tk.Radiobutton(scope_frame, text="Données seulement", variable=self.export_scope, value="data",
                       bg="#f0f0f0").grid(row=0, column=1, padx=8)
        tk.Radiobutton(scope_frame, text="Graphiques seulement", variable=self.export_scope, value="graphs",
                       bg="#f0f0f0").grid(row=0, column=2, padx=8)

        # Nombre de lignes d'aperçu pour le PDF
        preview_frame = tk.Frame(self, bg="#f0f0f0")
        preview_frame.pack(pady=4)
        tk.Label(preview_frame, text="Lignes d'aperçu dans le PDF:", bg="#f0f0f0").grid(row=0, column=0, padx=5)
        self.preview_rows = tk.IntVar(value=30)
        ttk.Spinbox(preview_frame, from_=5, to=200, textvariable=self.preview_rows, width=6).grid(row=0, column=1)

        # Boutons Export
        btn_frame = tk.Frame(self, bg="#f0f0f0")
        btn_frame.pack(pady=20)

        export_csv_btn = tk.Button(
            btn_frame,
            text="Exporter en CSV",
            command=lambda: self.export_data("csv"),
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12),
            relief="flat",
            width=16
        )
        export_csv_btn.grid(row=0, column=0, padx=10)

        export_pdf_btn = tk.Button(
            btn_frame,
            text="Exporter en PDF",
            command=lambda: self.export_data("pdf"),
            bg="#2196F3",
            fg="white",
            font=("Arial", 12),
            relief="flat",
            width=16
        )
        export_pdf_btn.grid(row=0, column=1, padx=10)

    def _ensure_dataframe(self, data):
        """Convertit en DataFrame si possible"""
        if isinstance(data, pd.DataFrame):
            return data
        if isinstance(data, pd.Series):
            return data.to_frame().T
        if isinstance(data, dict):
            return pd.DataFrame([data])
        if isinstance(data, (list, tuple)):
            return pd.DataFrame(data)
        try:
            return pd.DataFrame(data)
        except Exception:
            raise ValueError("Impossible de convertir les données en DataFrame.")

    def export_data(self, file_type):
        """Export CSV/PDF avec données et/ou graphiques"""
        choice_label = self.selected_option.get()
        if not choice_label:
            messagebox.showwarning("Avertissement", "Veuillez choisir un type de données à exporter.")
            return

        data_key = next((key for label, key in self.data_options if label == choice_label), None)
        data_obj = shared_data.get(data_key)

        # ✅ Vérifie si les données existent et ne sont pas vides
        if data_obj is None or (isinstance(data_obj, pd.DataFrame) and data_obj.empty):
            messagebox.showerror("Erreur", f"Aucune donnée disponible pour '{choice_label}'.")
            return

        figs = shared_data.get("figs", []) or []
        scope = self.export_scope.get()

        # === Export CSV ===
        if file_type == "csv":
            if scope == "graphs":
                messagebox.showwarning("Incompatible", "Export CSV uniquement possible pour les données.")
                return
            try:
                df = self._ensure_dataframe(data_obj)
            except ValueError as e:
                messagebox.showerror("Erreur", str(e))
                return

            file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("Fichier CSV", "*.csv")])
            if file_path:
                df.to_csv(file_path, index=False)
                messagebox.showinfo("Succès", f"Données '{choice_label}' exportées en CSV.")
            return

        # === Export PDF ===
        elif file_type == "pdf":
            if scope in ("both", "graphs") and not figs:
                if scope == "graphs":
                    messagebox.showwarning("Avertissement", "Aucun graphique disponible à exporter.")
                    return

            file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("Fichier PDF", "*.pdf")])
            if not file_path:
                return

            doc = SimpleDocTemplate(file_path, pagesize=landscape(A4))
            elements = []
            styles = getSampleStyleSheet()

            elements.append(Paragraph(f"Export des données : {choice_label}", styles['Heading1']))
            elements.append(Spacer(1, 12))

            # Données
            if scope in ("both", "data"):
                try:
                    df = self._ensure_dataframe(data_obj)
                    if not df.empty:
                        preview = df.head(self.preview_rows.get()).astype(str).fillna("")
                        table_data = [list(preview.columns)] + preview.values.tolist()
                        table = Table(table_data, repeatRows=1)
                        table.setStyle(TableStyle([
                            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 9),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                            ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
                        ]))
                        elements.append(table)
                        elements.append(Spacer(1, 12))
                except Exception as e:
                    elements.append(Paragraph(f"⚠ Impossible d'inclure le tableau : {e}", styles["Normal"]))

            # Graphiques
            if scope in ("both", "graphs") and figs:
                for i, fig in enumerate(figs, start=1):
                    try:
                        buf = io.BytesIO()
                        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
                        buf.seek(0)
                        elements.append(Paragraph(f"Graphique {i}", styles['Heading2']))
                        elements.append(Image(buf, width=500, height=300))
                        elements.append(Spacer(1, 12))
                    except Exception as e:
                        elements.append(Paragraph(f"⚠ Impossible d'inclure le graphique {i}: {e}", styles["Normal"]))

            try:
                doc.build(elements)
                what = {"both": "données et graphiques", "data": "données", "graphs": "graphiques"}[scope]
                messagebox.showinfo("Succès", f"Export PDF '{choice_label}' créé avec succès ({what}).")
            except Exception as e:
                messagebox.showerror("Erreur", f"Échec de la création du PDF : {e}")
