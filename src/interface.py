import os
import platform
import subprocess
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QFileDialog, QMessageBox)

class ZoneDetails(QFrame):
    """
    Panneau de détails et validation fonctionnelle.
    """
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedWidth(280)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<b>Détails du document</b>"))
        
        # Labels pour l'affichage
        self.label_nom = QLabel("Nom : -")
        self.label_info = QLabel("Info : -")
        layout.addWidget(self.label_nom)
        layout.addWidget(self.label_info)
        
        layout.addStretch()

        # Bouton d'action "Ouvrir"
        self.btn_ouvrir = QPushButton("Ouvrir le document")
        self.btn_ouvrir.setEnabled(False) # Désactivé par défaut
        self.btn_ouvrir.clicked.connect(self.action_ouvrir)
        layout.addWidget(self.btn_ouvrir)

    def mettre_a_jour(self, nom, info, chemin):
        """Fonction appelée lors d'une sélection dans la liste."""
        self.label_nom.setText(f"<b>Nom :</b> {nom}")
        self.label_info.setText(f"<b>Info :</b> {info}")
        self.chemin_actuel = chemin
        self.btn_ouvrir.setEnabled(True)

    def action_ouvrir(self):
        if not hasattr(self, 'chemin_actuel') or not os.path.exists(self.chemin_actuel):
            QMessageBox.warning(self, "Erreur", "Le fichier sélectionné est introuvable.")
            return

        systeme = platform.system()
        try:
            if systeme == "Windows":
                os.startfile(self.chemin_actuel)
            elif systeme == "Darwin":  # macOS
                subprocess.call(('open', self.chemin_actuel))
            else:  # Linux
                subprocess.call(('xdg-open', self.chemin_actuel))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de l'ouverture : {e}")

class LogiqueSelectionFichier:
    """
    Gestion de la sélection du fichier sur le PC.
    """
    def selectionner(self, parent_window):
        # Ouvre la fenêtre native du PC pour choisir un fichier
        fichier, _ = QFileDialog.getOpenFileName(parent_window, "Choisir un document à ajouter")
        return fichier if fichier else None
    

# TEST
class FenetrePrincipale(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Socle HF - Sélection et Actions")
        self.resize(600, 400)
        
        self.layout_global = QVBoxLayout(self)

        # 1. Zone de détails (Ta tâche)
        self.details = ZoneDetails()
        self.layout_global.addWidget(self.details)

        # 2. Bouton pour tester ta sélection de fichier
        self.btn_test_select = QPushButton("Tester la sélection de fichier (Parcourir)")
        self.btn_test_select.clicked.connect(self.tester_selecteur)
        self.layout_global.addWidget(self.btn_test_select)

    def tester_selecteur(self):
        outil = LogiqueSelectionFichier()
        path = outil.selectionner(self)
        if path:
            # On simule la sélection pour valider ton panneau de détails
            nom_fichier = os.path.basename(path)
            self.details.mettre_a_jour(nom_fichier, "Fichier sélectionné via explorateur", path)
            QMessageBox.information(self, "Validation", f"Sélection réussie !\nFichier : {nom_fichier}")