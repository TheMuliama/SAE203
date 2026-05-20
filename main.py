import sys
import os
# Éléments d'interface
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, QLineEdit, 
                             QLabel, QPushButton, QHeaderView, QDateEdit, QFileDialog,
                             QMessageBox, QTextEdit, QDialog, QFormLayout, QComboBox,
                             QDialogButtonBox)
# Logique de base et signaux
from PyQt6.QtCore import (Qt, QTimer, QObject, QDate) 
# Pour le visuel
from PyQt6.QtGui import (QIcon, QPixmap, QColor, QAction) 
from Interaction import AddDocumentDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Création de la fenêtre
        self.setWindowTitle("SAE 203 - Gestion documentaire")
        self.setWindowIcon(QIcon("pouce.png"))
        self.resize(1100, 700)

        self.createActions()
        self.createMenuBar()

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal horizontal
        main_layout = QHBoxLayout(central_widget)

        # On crée un conteneur pour la partie gauche de l'appli
        left_container = QWidget() 
        left_layout = QVBoxLayout(left_container)
        
        # La barre de recherche
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Rechercher un document...")
        left_layout.addWidget(self.search_bar)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Titre", "Auteur", "Date", "Catégorie"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        left_layout.addWidget(self.table)
        self.table.setSelectionBehavior(QHeaderView.SelectionBehavior.SelectRows)
        
        # On définit le mode de redimensionnement
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch) # Titre prend la place
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive) # Auteur réglable
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive) # Date petite
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive) # Catégorie petite
        #self.table.setColumnWidth(3, 100) # Largeur fixe pour Date
        #self.table.setColumnWidth(7, 200) # Largeur fixe pour Catégorie

        # Ajout de la partie gauche avec un gros stretch (4) pour qu'elle soit longue
        main_layout.addWidget(left_container, stretch=4)


        # On crée la partie droite (détails)
        right_panel = QWidget()
        #right_panel.setFixedWidth(300)
        right_panel.setStyleSheet("border-left: 1px solid #ddd;")
        right_layout = QVBoxLayout(right_panel)
        
        # Texte de la partie détails
        # Titre "Détails" stylisé
        self.details = QLabel("Fiche Détails")
        self.details.setStyleSheet("font-size: 20px; font-weight: bold; color: white; margin-bottom: 10px;")
        self.details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.details)

        # Labels pour les infos (on les garde en attributs self pour les modifier plus tard)
        self.info_titre = QLabel("Titre : -")
        self.info_auteur = QLabel("Auteur : -")
        self.info_date = QLabel("Date : -")
        self.info_cat = QLabel("Catégorie : -")
        for lbl in [self.info_titre, self.info_auteur, self.info_date, self.info_cat]:
            right_layout.addWidget(lbl)

        # Zone Description (Widget séparé)
        #right_layout.addSpacing(20)
        right_layout.addWidget(QLabel("<b>Description :</b>"))
        self.desc_box = QTextEdit() # Importez QTextEdit depuis QtWidgets
        self.desc_box.setReadOnly(True) # On ne peut pas modifier la description ici
        right_layout.addWidget(self.desc_box)
        right_layout.addStretch()
        
        # Layout horizontal pour les boutons côte à côte
        btn_layout = QHBoxLayout()
        self.btn_ouvrir = QPushButton("Ouvrir")
        self.btn_telecharger = QPushButton("Télécharger")
        btn_layout.addWidget(self.btn_ouvrir)
        btn_layout.addWidget(self.btn_telecharger)
        right_layout.addLayout(btn_layout)

        # --- CONNEXIONS ---
        # Quand on clique sur une ligne du tableau
        self.table.itemClicked.connect(self.afficherDetails)
        # Quand on tape dans la barre de recherche
        self.search_bar.textChanged.connect(self.filtrerTableau)
        # Bouton ouvrir
        self.btn_ouvrir.clicked.connect(self.ouvrirDocumentSelectionne)

        # On ajoute la partie droite au layout principal
        main_layout.addWidget(right_panel, stretch=2)
        

    def afficherDetails(self, item):
        """ Met à jour la partie droite quand on clique sur le tableau """
        row = item.row()
        titre = self.table.item(row, 0).text() if self.table.item(row, 0) else "-"
        auteur = self.table.item(row, 1).text() if self.table.item(row, 1) else "-"
        date = self.table.item(row, 2).text() if self.table.item(row, 2) else "-"
        cat = self.table.item(row, 3).text() if self.table.item(row, 3) else "-"

        self.info_titre.setText(f"Titre : {titre}")
        self.info_auteur.setText(f"Auteur : {auteur}")
        self.info_date.setText(f"Date : {date}")
        self.info_cat.setText(f"Catégorie : {cat}")
        self.desc_box.setText(f"Description incroyable de : {titre}")

    def filtrerTableau(self):
        """ Recherche dynamique dans le tableau """
        filtre = self.search_bar.text().lower()
        for row in range(self.table.rowCount()):
            match = False
            # On vérifie toutes les colonnes (Titre, Auteur, etc.)
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and filtre in item.text().lower():
                    match = True
                    break
            
            # Cache ou montre la ligne selon le résultat
            self.table.setRowHidden(row, not match)

    def newDocument(self):
        # Le programme va aller chercher AddDocumentDialog dans dialogs.py
        dialog = AddDocumentDialog(self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            print(f"On ajoute : {data['titre']} par {data['auteur']}")
            # Ici on met la logique pour ajouter au tableau (insertRow...)

    def ouvrirDocumentSelectionne(self):
        import os
        current_row = self.table.currentRow()
        if current_row != -1:
            # On récupère le chemin caché dans la colonne 0
            file_path = self.table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
            if file_path and os.path.exists(file_path):
                os.startfile(file_path) # Ouvre le fichier avec le logiciel par défaut
            else:
                QMessageBox.warning(self, "Erreur", "Fichier introuvable sur le disque.")

    def telechargerDocument(self):
        import shutil
        current_row = self.table.currentRow()
        if current_row != -1:
            file_path = self.table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
            if file_path:
                dest_path, _ = QFileDialog.getSaveFileName(self, "Enregistrer sous", os.path.basename(file_path))
                if dest_path:
                    shutil.copy(file_path, dest_path) # Copie physique du fichier
                    QMessageBox.information(self, "Succès", "Fichier téléchargé/copié avec succès.")

    def createActions(self):
        # Partie Fichier
        # Nouveau
        self.actNew = QAction(QIcon("assets/icons/papier.png"), "&Nouveau", self)
        self.actNew.setShortcut("Ctrl+N")
        self.actNew.setStatusTip("Nouveau document")
        self.actNew.triggered.connect(self.newDocument)
        
        self.actArchive = QAction(QIcon("assets/icons/papier.png"), "&Archive", self)
        self.actArchive.setShortcut("Ctrl+R")
        self.actArchive.setStatusTip("Archive des documents récents")
        #self.actArchive.triggered.connect(self.newDocument)

        # Quitter l'appli
        self.actExit = QAction(QIcon("assets/icons/quitter.png"), "Quitter", self)
        self.actExit.setShortcut("Alt+F4")
        self.actExit.setStatusTip("Quitter")
        self.actExit.triggered.connect(self.quitApp)

        # Partie Édition 
        # Exporter
        self.actExport = QAction(QIcon("assets/icons/export.jpg"),"&Exporter", self)
        self.actExport.setShortcut("Ctrl+E")
        self.actExport.setStatusTip("Exporter le document")
        self.actExport.triggered.connect(self.exportDocument)

        # Supprimer
        self.actDelete = QAction(QIcon("assets/icons/delete.png"),"&Supprimer un document", self)
        self.actExport.setShortcut("Ctrl+D")
        self.actDelete.setStatusTip("Supprimer le document sélectionné")
        self.actDelete.triggered.connect(self.deleteDocument)

        # Partie Importer
        # Sélectiionner un document à importer
        self.actImport = QAction(QIcon("assets/icons/ouvrir.png"), "&Sélectionner un document...", self)
        self.actImport.setShortcut("Ctrl+O")
        self.actImport.setStatusTip("Importer un document depuis votre ordinateur")
        self.actImport.triggered.connect(self.importDocument)

    def createMenuBar(self):
        # Barre du menu
        # Partie pour Fichier
        menu = self.menuBar()
        file = menu.addMenu("&Fichier")
        file.addAction(self.actNew)
        file.addSeparator()
        file.addAction(self.actArchive)
        file.addSeparator()
        file.addAction(self.actExport)
        file.addSeparator()
        file.addAction(self.actExit)

        # Partie pour Édition
        edition = menu.addMenu("&Édition")
        edition.addAction(self.actDelete)
        
        # Partie pour le reste
        import_menu = menu.addMenu("&Importer")
        import_menu.addAction(self.actImport)

        file_menu = menu.addMenu("Aide")
        file_menu.addAction("Guide")
        file_menu.addAction("Contact")


    def quitApp(self):
        self.close()

    def exportDocument(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Exportation", "Le tableau est vide !")
            return

        # Ouvrir la boîte de dialogue "Enregistrer sous"
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Exporter les données", 
            "export_donnees.txt", 
            "Fichier Texte (*.txt);;Tous les fichiers (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    # On parcourt les lignes et les colonnes
                    for row in range(self.table.rowCount()):
                        row_data = []
                        for col in range(self.table.columnCount()):
                            item = self.table.item(row, col)
                            # On récupère le texte ou un vide si la cellule est vide
                            text = item.text() if item else ""
                            row_data.append(text)
                        
                        # On écrit la ligne dans le fichier
                        f.write(" | ".join(row_data) + "\n")
                
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible d'exporter : {e}")

    def editDocument(self):
        print("Action : Modifier le document")

    def deleteDocument(self):
        current_row = self.table.currentRow()

        if current_row != -1: # Une ligne est sélectionnée
            confirm = QMessageBox.question(
                self, "Confirmation", 
                "Voulez-vous vraiment supprimer ce document ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if confirm == QMessageBox.StandardButton.Yes:
                self.table.removeRow(current_row) # Supprime la ligne du tableau
        else:
            QMessageBox.warning(self, "Attention", "Veuillez cliquer sur une ligne du tableau d'abord.")

    def importDocument(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner un document", "", 
            "Tous les fichiers (*);;PDF (*.pdf);;Images (*.png *.jpg)"
        )

        if file_path:
            # 1. Extraire le nom du fichier depuis le chemin complet
            import os
            nom_fichier = os.path.basename(file_path)
            date_import = QDate.currentDate().toString("dd/MM/yyyy")

            # 2. Insérer une nouvelle ligne au début (index 0)
            self.table.insertRow(0)

            # 3. Remplir les colonnes (Titre, Auteur, Date, Catégorie)
            self.table.setItem(0, 0, QTableWidgetItem(nom_fichier))
            self.table.setItem(0, 1, QTableWidgetItem("Moi")) # Auteur par défaut
            self.table.setItem(0, 2, QTableWidgetItem(date_import))
            self.table.setItem(0, 3, QTableWidgetItem("Importé"))


def main():
    app = QApplication(sys.argv)    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()