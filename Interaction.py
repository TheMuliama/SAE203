# dialogs.py
from pathlib import Path

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QFormLayout,
                             QLineEdit, QComboBox, QTextEdit, QDialogButtonBox,
                             QPushButton, QFileDialog, QDateEdit)

class AddDocumentDialog(QDialog):
    def __init__(self, parent=None, categories=None):
        super().__init__(parent)
        self.setWindowTitle("Ajouter un document")
        self.setFixedWidth(400)
        self.selected_file = None
        
        layout = QVBoxLayout(self)
        
        header = QLabel("Informations sur le nouveau document")
        header.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 10px;")
        layout.addWidget(header)

        form = QFormLayout()
        self.titre_input = QLineEdit()
        self.titre_input.setPlaceholderText("Saisissez le titre...")
        
        self.auteur_input = QLineEdit()
        self.auteur_input.setPlaceholderText("Saisissez l'auteur...")

        self.date_input = QDateEdit(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("yyyy-MM-dd")

        self.stockage_input = QComboBox()
        self.stockage_input.addItems(["local", "partage"])
        
        self.cat_input = QComboBox()
        self.cat_input.addItems(categories or ["Rapport", "Projet", "Technique"])
        
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Saisissez la description...")
        self.desc_input.setMinimumHeight(150)

        self.file_label = QLabel("Aucun fichier sélectionné")
        self.file_button = QPushButton("Sélectionner un fichier")
        self.file_button.clicked.connect(self.select_file)
        
        form.addRow("Titre :", self.titre_input)
        form.addRow("Auteur :", self.auteur_input)
        form.addRow("Date :", self.date_input)
        form.addRow("Stockage :", self.stockage_input)
        form.addRow("Catégorie :", self.cat_input)
        form.addRow("Description :", self.desc_input)
        form.addRow(self.file_button, self.file_label)
        
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
            "date": self.date_input.date().toString("yyyy-MM-dd"),
            "stockage": self.stockage_input.currentText(),
            "categorie": self.cat_input.currentText(),
            "description": self.desc_input.toPlainText(),
            "fichier": self.selected_file,
        }

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir un document à ajouter",
            "",
            "Documents (*.pdf *.doc *.docx *.xls *.xlsx);;Tous les fichiers (*)",
        )
        if not file_path:
            return

        self.selected_file = file_path
        self.file_label.setText(Path(file_path).name)
        if not self.titre_input.text().strip():
            self.titre_input.setText(Path(file_path).stem.replace("_", " ").strip())
