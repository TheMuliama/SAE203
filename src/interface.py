import os
import platform
import shutil
import subprocess
from pathlib import Path

# Éléments d'interface
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem, QLineEdit,
                             QLabel, QPushButton, QHeaderView, QDateEdit, QFileDialog,
                             QMessageBox, QTextEdit, QDialog, QFormLayout, QComboBox,
                             QDialogButtonBox)
# Logique de base et signaux
from PyQt6.QtCore import (Qt, QTimer, QObject, QDate, QEvent)
# Pour le visuel
from PyQt6.QtGui import (QIcon, QPixmap, QColor, QAction, QStandardItem, QStandardItemModel)

from src.database import build_repository
from src.logic import DocumentInput, LogicService, SearchFilters, ValidationError


class CheckableComboBox(QComboBox):
    """Menu déroulant permettant de cocher plusieurs catégories."""

    def __init__(self, placeholder, parent=None):
        super().__init__(parent)
        self.placeholder = placeholder
        self._items_model = QStandardItemModel(self)
        self.setModel(self._items_model)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.lineEdit().setReadOnly(True)
        self.view().viewport().installEventFilter(self)
        self._update_display_text()

    def add_checkable_items(self, values):
        for value in values:
            item = QStandardItem(value)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsSelectable
            )
            item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
            self._items_model.appendRow(item)
        self._update_display_text()

    def checked_items(self):
        checked = []
        for row in range(self._items_model.rowCount()):
            item = self._items_model.item(row)
            if item and item.checkState() == Qt.CheckState.Checked:
                checked.append(item.text())
        return checked

    def eventFilter(self, watched, event):
        if watched == self.view().viewport():
            if event.type() == QEvent.Type.MouseButtonPress:
                return True

            if event.type() == QEvent.Type.MouseButtonRelease:
                index = self.view().indexAt(event.position().toPoint())
                if index.isValid():
                    self._toggle_item(index)
                return True

        return super().eventFilter(watched, event)

    def _toggle_item(self, index):
        item = self._items_model.itemFromIndex(index)
        if not item:
            return

        new_state = (
            Qt.CheckState.Unchecked
            if item.checkState() == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )
        item.setCheckState(new_state)
        self._update_display_text()

    def _update_display_text(self):
        checked = self.checked_items()
        self.lineEdit().setText(", ".join(checked) if checked else self.placeholder)


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

        self.cat_input = CheckableComboBox("Sélectionner des catégories")
        self.cat_input.add_checkable_items(categories or ["Rapport", "Projet", "Technique"])

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
        form.addRow("Catégories :", self.cat_input)
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
            "categories": self.cat_input.checked_items(),
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


class MainWindow(QMainWindow):
    def __init__(self, logic_service=None, project_root=None):
        # Initialise la fenêtre principale et prépare les services utilisés par l'interface.
        super().__init__()
        self.project_root = Path(project_root or Path(__file__).resolve().parent.parent)
        self.logic = logic_service or LogicService(build_repository(self.project_root))

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
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

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
        self.btn_telecharger.clicked.connect(self.telechargerDocument)

        # On ajoute la partie droite au layout principal
        main_layout.addWidget(right_panel, stretch=2)
        self.chargerDocuments()

    def chargerDocuments(self):
        """Charge les documents depuis SQLite dans le tableau."""
        # Récupère les documents via la couche logique puis les affiche dans le tableau.
        try:
            documents = self.logic.search_documents(SearchFilters())
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible de charger les documents : {exc}")
            return

        self.table.setRowCount(0)
        for document in documents:
            row = self.table.rowCount()
            self.table.insertRow(row)
            categories = ", ".join(document.get("categorie") or []) or "-"
            valeurs = [
                document.get("titre", ""),
                document.get("auteur", ""),
                document.get("date", ""),
                categories,
            ]

            for col, valeur in enumerate(valeurs):
                item = QTableWidgetItem(str(valeur))
                item.setData(Qt.ItemDataRole.UserRole, document)
                self.table.setItem(row, col, item)

    def documentSelectionne(self):
        # Retourne le document complet associé à la ligne sélectionnée.
        current_row = self.table.currentRow()
        if current_row == -1:
            return None

        item = self.table.item(current_row, 0)
        if not item:
            return None

        document = item.data(Qt.ItemDataRole.UserRole)
        return document if isinstance(document, dict) else None

    def cheminDocumentSelectionne(self):
        # Calcule le chemin disque du document sélectionné.
        document = self.documentSelectionne()
        if not document:
            return None

        ressource = document.get("chemin_fichier") or document.get("ressource")
        if not ressource:
            return None

        chemin = Path(ressource)
        if not chemin.is_absolute():
            chemin = self.project_root / chemin
        return chemin

    def afficherDetails(self, item):
        """ Met à jour la partie droite quand on clique sur le tableau """
        # Affiche les informations principales du document sélectionné.
        row = item.row()
        titre = self.table.item(row, 0).text() if self.table.item(row, 0) else "-"
        auteur = self.table.item(row, 1).text() if self.table.item(row, 1) else "-"
        date = self.table.item(row, 2).text() if self.table.item(row, 2) else "-"
        cat = self.table.item(row, 3).text() if self.table.item(row, 3) else "-"

        self.info_titre.setText(f"Titre : {titre}")
        self.info_auteur.setText(f"Auteur : {auteur}")
        self.info_date.setText(f"Date : {date}")
        self.info_cat.setText(f"Catégorie : {cat}")
        document = self.documentSelectionne()
        description = document.get("description") if document else ""
        self.desc_box.setText(description or f"Aucune description pour : {titre}")

    def filtrerTableau(self):
        """ Recherche dynamique dans le tableau """
        # Cache les lignes qui ne correspondent pas au texte recherché.
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

    def importDocument(self):
        # Ouvre la boîte de dialogue d'import et enregistre le document en base.
        dialog = AddDocumentDialog(self, self.logic.list_categories())

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                if not data["fichier"]:
                    raise ValidationError("Veuillez sélectionner un fichier.")
                if not data["titre"].strip():
                    raise ValidationError("Le titre est obligatoire.")
                if not data["auteur"].strip():
                    raise ValidationError("L'auteur est obligatoire.")

                relative_resource = self.copierFichierDansStockage(
                    data["fichier"],
                    data["stockage"],
                )
                suffix = Path(data["fichier"]).suffix.upper().lstrip(".")

                document_id = self.logic.add_document(
                    DocumentInput(
                        titre=data["titre"],
                        auteur=data["auteur"],
                        date_document=data["date"],
                        ressource=relative_resource,
                        description=data["description"],
                        categories=data["categories"],
                        stockage=data["stockage"],
                        chemin_fichier=relative_resource,
                        type_fichier=suffix,
                    )
                )
                QMessageBox.information(self, "Ajout", f"Document ajouté avec succès (id {document_id}).")
                self.chargerDocuments()
            except ValidationError as exc:
                QMessageBox.warning(self, "Validation", str(exc))
            except Exception as exc:
                QMessageBox.critical(self, "Erreur", f"Impossible d'ajouter le document : {exc}")

    def copierFichierDansStockage(self, source_file, stockage):
        # Copie le fichier choisi dans l'espace applicatif et retourne son chemin relatif.
        source = Path(source_file)
        target_dir = self.project_root / "documents" / stockage
        target_dir.mkdir(parents=True, exist_ok=True)

        target = target_dir / source.name
        if target.exists():
            stem = source.stem
            suffix = source.suffix
            index = 1
            while target.exists():
                target = target_dir / f"{stem}_{index}{suffix}"
                index += 1

        shutil.copy2(source, target)
        return str(target.relative_to(self.project_root)).replace("\\", "/")

    def ouvrirDocumentSelectionne(self):
        # Ouvre le fichier du document sélectionné avec l'application système.
        file_path = self.cheminDocumentSelectionne()
        if not file_path or not file_path.exists():
            QMessageBox.warning(self, "Erreur", "Fichier introuvable sur le disque.")
            return

        try:
            systeme = platform.system()
            if systeme == "Windows":
                os.startfile(str(file_path))
            elif systeme == "Darwin":
                subprocess.call(("open", str(file_path)))
            else:
                subprocess.call(("xdg-open", str(file_path)))
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible d'ouvrir le document : {exc}")

    def telechargerDocument(self):
        """
        Copie le fichier du document sélectionné vers un emplacement choisi.
        """

        file_path = self.cheminDocumentSelectionne()
        if not file_path or not file_path.exists():
            QMessageBox.warning(self, "Erreur", "Fichier introuvable sur le disque.")
            return

        dest_path, _ = QFileDialog.getSaveFileName(self, "Enregistrer sous", file_path.name)
        if dest_path:
            shutil.copy(file_path, dest_path) # Copie physique du fichier
            QMessageBox.information(self, "Succès", "Fichier téléchargé/copié avec succès.")

    def createActions(self):
        """
         Crée les actions de menu et relie chaque action à sa méthode.
        """
        
        ######## Partie Fichier ########
        self.actArchive = QAction(QIcon("assets/icons/papier.png"), "&Archive", self)
        self.actArchive.setShortcut("Ctrl+R")
        self.actArchive.setStatusTip("Archive des documents récents")
        #self.actArchive.triggered.connect(self.importDocument)

        # Quitter l'appli
        self.actExit = QAction(QIcon("assets/icons/quitter.png"), "Quitter", self)
        self.actExit.setShortcut("Alt+F4")
        self.actExit.setStatusTip("Quitter")
        self.actExit.triggered.connect(self.quitApp)

        ####### Partie Édition ######
        # Exporter
        self.actExport = QAction(QIcon("assets/icons/export.jpg"),"&Exporter", self)
        self.actExport.setShortcut("Ctrl+E")
        self.actExport.setStatusTip("Exporter le document")
        self.actExport.triggered.connect(self.exportDocument)

        # Supprimer
        self.actDelete = QAction(QIcon("assets/icons/delete.png"),"&Supprimer un document", self)
        self.actDelete.setShortcut("Ctrl+D")
        self.actDelete.setStatusTip("Supprimer le document sélectionné")
        self.actDelete.triggered.connect(self.deleteDocument)
 
        ######## Partie Importer ########
        self.actImport = QAction(QIcon("assets/icons/ouvrir.png"), "&Sélectionner un document...", self)
        self.actImport.setShortcut("Ctrl+O")
        self.actImport.setStatusTip("Importer un document depuis votre ordinateur")
        self.actImport.triggered.connect(self.importDocument)


    def createMenuBar(self):
        """
        Construit la barre de menu à partir des actions créées.
        """
        
        # Partie pour Fichier
        menu = self.menuBar()
        file = menu.addMenu("&Fichier")
        file.addAction(self.actArchive)
        file.addSeparator()
        file.addAction(self.actExport)
        file.addSeparator()
        file.addAction(self.actExit)

        # Partie pour Édition
        edition = menu.addMenu("&Édition")
        edition.addAction(self.actDelete)

        import_menu = menu.addMenu("&Importer")
        import_menu.addAction(self.actImport)

        file_menu = menu.addMenu("Aide")
        file_menu.addAction("Guide")
        file_menu.addAction("Contact")


    def quitApp(self):
        """
        Ferme la fenêtre pour quitter l'application
        """

        self.close()

    def exportDocument(self):
        """
        Exporte le contenu actuel du tableau dans un fichier texte.
        """

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
        """
        Point d'entrée prévu pour modifier le document sélectionné.
        """
        print("Action : Modifier le document")

    def deleteDocument(self):
        """
        Supprime le document sélectionné après confirmation.
        """
        document = self.documentSelectionne()
        if not document:
            QMessageBox.warning(self, "Attention", "Veuillez cliquer sur une ligne du tableau d'abord.")
            return

        document_id = document.get("id")
        if not document_id:
            QMessageBox.warning(self, "Erreur", "Impossible d'identifier le document sélectionné.")
            return
        user_id = document.get("user_id")
        if not user_id:
            QMessageBox.warning(self, "Erreur", "Impossible d'identifier le propriétaire du document.")
            return

        confirm = QMessageBox.question(
            self, "Confirmation",
            "Voulez-vous vraiment supprimer ce document ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            self.logic.delete_document(int(document_id), int(user_id))
            self.chargerDocuments()
            self.info_titre.setText("Titre : -")
            self.info_auteur.setText("Auteur : -")
            self.info_date.setText("Date : -")
            self.info_cat.setText("Catégorie : -")
            self.desc_box.clear()
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible de supprimer le document : {exc}")
