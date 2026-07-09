import tkinter as tk
from tkinter import ttk
from shared_data import shared_data  # Import du dictionnaire partagé

# Import des onglets
from onglets.overview_page import OverviewPage
from onglets.rfm_page import RFMPage
from onglets.segmentation_page import SegmentationPage
from onglets.simulation_page import SimulationPage
from onglets.risque_desabonnement_page import RisqueDesabonnementPage
from onglets.anomalies_page import AnomaliesPage
from onglets.forecast_page import ForecastPage
from onglets.prediction_page import PredictionPage
from onglets.ai_page import AIPage
from onglets.filter_page import FilterPage
from onglets.export_page import ExportPage


class InsightMarkApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("InsightMark")
        self.geometry("1200x700")
        self.configure(bg="#1e1e2f")

        # Barre latérale
        self.sidebar = tk.Frame(self, width=200, bg="#2c2c3c")
        self.sidebar.pack(side="left", fill="y")

        # Zone principale
        self.main_frame = tk.Frame(self, bg="#f0f0f0")
        self.main_frame.pack(side="right", expand=True, fill="both")

        # Dictionnaire des pages
        self.pages = {
            "Vue d'ensemble": OverviewPage,
            "Analyse RFM": RFMPage,
            "Segmentation": SegmentationPage,
            "Simulation": SimulationPage,
            "Risque de désabonnement": RisqueDesabonnementPage,
            "Anomalies": AnomaliesPage,
            "Prévisions": ForecastPage,
            "Prédictions": PredictionPage,
            "IA": AIPage,
            "Filtres": FilterPage,
            "Export": ExportPage
        }

        # Sauvegarde des boutons pour changer leur style
        self.buttons = {}

        # Boutons de navigation
        for name in self.pages:
            button = tk.Button(
                self.sidebar,
                text=name,
                font=("Arial", 10),
                bg="#2c2c3c",
                fg="white",
                bd=0,
                relief="flat",
                anchor="w",
                padx=20,
                command=lambda name=name: self.show_page(name)
            )
            button.pack(fill="x", pady=2)
            self.buttons[name] = button

        # Page par défaut
        default_page = list(self.pages.keys())[0]
        self.show_page(default_page)

    def show_page(self, name):
        """Affiche la page choisie et met à jour le style du bouton actif"""
        # Réinitialiser tous les boutons
        for btn in self.buttons.values():
            btn.config(bg="#2c2c3c", fg="white", font=("Arial", 10))

        # Mettre en évidence le bouton actif
        self.buttons[name].config(bg="#00cec9", fg="black", font=("Arial", 10, "bold"))

        # Charger la page
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        page_class = self.pages[name]
        page = page_class(self.main_frame)
        page.pack(expand=True, fill="both")


if __name__ == "__main__":
    app = InsightMarkApp()
    app.mainloop()
