# dialogs.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QFormLayout, 
                             QLineEdit, QComboBox, QTextEdit, QDialogButtonBox)
from PyQt6.QtCore import Qt

class AddDocumentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajouter un document")
        self.setFixedWidth(400)
        
        layout = QVBoxLayout(self)
        
        header = QLabel("Informations sur le nouveau document")
        header.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 10px;")
        layout.addWidget(header)

        form = QFormLayout()
        self.titre_input = QLineEdit()
        self.titre_input.setPlaceholderText("Saisissez le titre...")
        
        self.auteur_input = QLineEdit()
        self.auteur_input.setPlaceholderText("Saisissez l'auteur...")
        
        self.cat_input = QComboBox()
        self.cat_input.addItems(["Rapport", "Projet", "Technique", "Autre"])
        
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Saisissez la description...")
        self.desc_input.setMinimumHeight(150)
        
        form.addRow("Titre :", self.titre_input)
        form.addRow("Auteur :", self.auteur_input)
        form.addRow("Catégorie :", self.cat_input)
        form.addRow("Description :", self.desc_input)
        
        layout.addLayout(form)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Ajouter")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def get_data(self):
        return {
            "titre": self.titre_input.text(),
            "auteur": self.auteur_input.text(),
            "categorie": self.cat_input.currentText(),
            "description": self.desc_input.toPlainText()
        }