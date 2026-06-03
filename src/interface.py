import os
import platform
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# Éléments d'interface
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QApplication,
                             QHBoxLayout, QTableWidget, QTableWidgetItem, QLineEdit,
                             QLabel, QPushButton, QHeaderView, QDateEdit, QFileDialog,
                             QMessageBox, QTextEdit, QDialog, QFormLayout, QComboBox,
                             QDialogButtonBox, QRadioButton, QButtonGroup, QSpinBox)
# Logique de base et signaux
from PyQt6.QtCore import (Qt, QTimer, QObject, QDate, QEvent)
# Pour le visuel
from PyQt6.QtGui import (QIcon, QPixmap, QColor, QAction, QStandardItem, QStandardItemModel, QFont)

from src.database import build_repository
from src.logic import DocumentInput, LogicService, SearchFilters, ValidationError


# ==============================================================================
# FENÊTRE DE PRÉFÉRENCES (BOUTONS RADIO ET STYLE CORRIGÉS)
# ==============================================================================
class SowedropPreferencesDialog(QDialog):
    def __init__(self, parent=None, actuel_theme="Clair", actuelle_taille=10):
        super().__init__(parent)
        self.setWindowTitle("Préférences")
        self.setFixedWidth(360)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Section Sélection du Thème
        lbl_theme = QLabel("<b>Sélectionnez le thème :</b>")
        layout.addWidget(lbl_theme)
        
        self.group_theme = QButtonGroup(self)
        self.radio_clair = QRadioButton("Clair (Orange & Blanc)")
        self.radio_sombre = QRadioButton("Sombre (Orange & Noir)")
        
        self.group_theme.addButton(self.radio_clair)
        self.group_theme.addButton(self.radio_sombre)
        
        layout.addWidget(self.radio_clair)
        layout.addWidget(self.radio_sombre)
        
        if actuel_theme == "Sombre":
            self.radio_sombre.setChecked(True)
        else:
            self.radio_clair.setChecked(True)
            
        # Section Taille de Police Globale
        lbl_police = QLabel("<b>Taille de la police globale :</b>")
        layout.addWidget(lbl_police)
        
        h_layout_police = QHBoxLayout()
        self.spin_font = QSpinBox()
        self.spin_font.setRange(8, 24)
        self.spin_font.setValue(actuelle_taille)
        self.spin_font.setFixedWidth(80)
        
        lbl_pt = QLabel("pt")
        
        h_layout_police.addWidget(self.spin_font)
        h_layout_police.addWidget(lbl_pt)
        h_layout_police.addStretch()
        layout.addLayout(h_layout_police)
        
        # Boutons d'action Enregistrer / Annuler
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Enregistrer")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)


def trouver_logo():
    extensions = [".png", ".webp", ".jpg", ".jpeg"]
    for ext in extensions:
        if os.path.exists(f"pouce{ext}"):
            return f"pouce{ext}"
    return "pouce.png"


class ContactDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Contacter SoweDrop")
        self.setFixedWidth(380)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        logo_lbl = QLabel()
        chemin_logo = trouver_logo()
        pixmap = QPixmap(chemin_logo)
        if not pixmap.isNull():
            logo_lbl.setPixmap(pixmap.scaled(90, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(logo_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        
        title = QLabel("Support SoweDrop")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 10px; margin-bottom: 10px;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        
        info = QLabel("Une question ou un bug ?\n\n📧 Contact : support@sowedrop.com\n🌐 Site officiel : https://heloweeze.github.io/SoweDrop/\n\nVersion 1.0.0 (3 juin 2026)")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("font-size: 13px; margin-bottom: 15px;")
        layout.addWidget(info)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btn_box.button(QDialogButtonBox.StandardButton.Ok).setText("Fermer")
        btn_box.accepted.connect(self.accept)
        layout.addWidget(btn_box, alignment=Qt.AlignmentFlag.AlignCenter)


class CheckableComboBox(QComboBox):
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

        # Mots-clé
        self.mots_cles_input = QLineEdit()
        self.mots_cles_input.setPlaceholderText("Ex: urgent; rapport; compta (séparés par ';')")

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
        form.addRow("Mots-clés :", self.mots_cles_input)
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
        # 1. On découpe les mots-clés saisis par l'utilisateur
        mots_bruts = self.mots_cles_input.text().split(";")
        mots_nettoyes = [m.strip() for m in mots_bruts if m.strip()]

        # 2. On retourne le dictionnaire complet
        return {
            "titre": self.titre_input.text(),
            "auteur": self.auteur_input.text(),
            "date": self.date_input.date().toString("yyyy-MM-dd"),
            "stockage": self.stockage_input.currentText(),
            "categories": self.cat_input.checked_items(),
            "mots_cles": mots_nettoyes,
            "description": self.desc_box.toPlainText() if hasattr(self, 'desc_box') else self.desc_input.toPlainText(),
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
        super().__init__()
        self.project_root = Path(project_root or Path(__file__).resolve().parent.parent)
        self.logic = logic_service or LogicService(build_repository(self.project_root))

        self.setWindowTitle("SoweDrop")
        
        chemin_logo = trouver_logo()
        self.setWindowIcon(QIcon("./assets/icons/logo.webp"))
        self.resize(1100, 700)

        self.createActions()
        self.createMenuBar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QHBoxLayout(central_widget)

        # PAGE D'ACCUEIL CENTRÉE
        self.accueil_container = QWidget()
        accueil_layout = QVBoxLayout(self.accueil_container)
        accueil_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.logo_label = QLabel()
        pixmap = QPixmap("./assets/icons/logo.webp")
        if not pixmap.isNull():
            self.logo_label.setPixmap(pixmap.scaled(130, 130, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        accueil_layout.addWidget(self.logo_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.welcome_label = QLabel("Bienvenue sur SoweDrop")
        self.welcome_label.setObjectName("welcomeLabel")
        accueil_layout.addWidget(self.welcome_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.search_bar_accueil = QLineEdit()
        self.search_bar_accueil.setPlaceholderText("Rechercher un document et appuyez sur Entrée...")
        self.search_bar_accueil.setFixedWidth(520)
        self.search_bar_accueil.setObjectName("searchBarAccueil")
        self.search_bar_accueil.returnPressed.connect(self.executer_recherche_accueil)
        accueil_layout.addWidget(self.search_bar_accueil, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.main_layout.addWidget(self.accueil_container, stretch=1)

        # INTERFACE CLASSIQUE
        self.left_container = QWidget()
        self.left_layout = QVBoxLayout(self.left_container)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Filtrer les résultats...")
        self.left_layout.addWidget(self.search_bar)
        
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Titre", "Auteur", "Date", "Catégorie"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        
        self.left_layout.addWidget(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)

        self.right_panel = QWidget()
        self.right_panel.setObjectName("rightPanel")
        self.right_layout = QVBoxLayout(self.right_panel)

        self.details = QLabel("Fiche Détails")
        self.details.setObjectName("detailsHeader")
        self.details.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        self.details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.right_layout.addWidget(self.details)

        self.info_titre = QLabel("Titre : -")
        self.info_auteur = QLabel("Auteur : -")
        self.info_date = QLabel("Date : -")
        self.info_cat = QLabel("Catégorie : -")
        self.info_mots = QLabel("Mots-clés : -")
        for lbl in [self.info_titre, self.info_auteur, self.info_date, self.info_cat, self.info_mots]:
            self.right_layout.addWidget(lbl)

        self.label_desc_title = QLabel("Description :")
        f_desc = self.label_desc_title.font()
        f_desc.setBold(True)
        self.label_desc_title.setFont(f_desc)
        
        self.right_layout.addWidget(self.label_desc_title)
        self.desc_box = QTextEdit()
        self.desc_box.setReadOnly(True)
        self.right_layout.addWidget(self.desc_box)
        self.right_layout.addStretch()

        btn_layout = QHBoxLayout()
        self.btn_ouvrir = QPushButton("Ouvrir")
        self.btn_telecharger = QPushButton("Télécharger")
        btn_layout.addWidget(self.btn_ouvrir)
        btn_layout.addWidget(self.btn_telecharger)
        self.right_layout.addLayout(btn_layout)

        self.main_layout.addWidget(self.left_container, stretch=4)
        self.main_layout.addWidget(self.right_panel, stretch=2)
        
        self.left_container.hide()
        self.right_panel.hide()

        self.table.itemClicked.connect(self.afficherDetails)
        self.search_bar.textChanged.connect(self.filtrerTableau)
        self.btn_ouvrir.clicked.connect(self.ouvrirDocumentSelectionne)
        self.btn_telecharger.clicked.connect(self.telechargerDocument)

        self.chargerDocuments()
        
        self.actuelle_theme = "Clair"
        self.appliquer_theme_clair()

    def executer_recherche_accueil(self):
        texte_saisi = self.search_bar_accueil.text().strip()
        if texte_saisi != "":
            self.accueil_container.hide()
            self.left_container.show()
            self.right_panel.show()
            self.search_bar.setText(texte_saisi)
            self.search_bar.setFocus()

    def chargerDocuments(self):
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
        current_row = self.table.currentRow()
        if current_row == -1:
            return None
        item = self.table.item(current_row, 0)
        if not item:
            return None
        document = item.data(Qt.ItemDataRole.UserRole)
        return document if isinstance(document, dict) else None

    def cheminDocumentSelectionne(self):
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

        # --- BLOC AJOUTÉ POUR LES MOTS-CLÉS ---
        document = self.documentSelectionne()
        mots = "-"
        if document:
            # On va chercher la liste des mots-clés associée au document
            mots_liste = document.get("mots_cles") or []
            if mots_liste:
                mots = ", ".join(mots_liste)
        self.info_mots.setText(f"Mots-clés : {mots}")
        # --------------------------------------

        description = document.get("description") if document else ""
        self.desc_box.setText(description or f"Aucune description pour : {titre}")

    def filtrerTableau(self):
        filtre = self.search_bar.text().lower()
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and filtre in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)

    def importDocument(self):
        """ Ouvre la boîte de dialogue d'import et enregistre le document en base. """
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

                # 1. Préparation du dictionnaire pour la BDD
                doc_payload = {
                    "titre": data["titre"],
                    "auteur": data["auteur"],
                    "date_document": data["date"],
                    "ressource": relative_resource,
                    "description": data["description"],
                    "stockage": data["stockage"],
                    "type_fichier": suffix
                }

                # 2. Utilisation de self.logic.repository (Fidèle à ton fichier logic.py !)
                db_repo = self.logic.repository

                # 3. Insertion du document principal
                document_id = db_repo.insert_document(doc_payload)

                # 4. Liaison des catégories
                if data["categories"]:
                    db_repo.link_categories_to_document(document_id, data["categories"])

                # 5. Liaison des mots-clés saisis
                if data["mots_cles"]:
                    db_repo.link_keywords_to_document(document_id, data["mots_cles"])

                # 6. Ajout de l'historique
                db_repo.add_history(document_id, "Importation du document avec mots-clés")

                QMessageBox.information(self, "Ajout", f"Document ajouté avec succès (id {document_id}).")
                self.chargerDocuments()

            except ValidationError as exc:
                QMessageBox.warning(self, "Validation", str(exc))
            except Exception as exc:
                QMessageBox.critical(self, "Erreur", f"Impossible d'ajouter le document : {exc}")

    def copierFichierDansStockage(self, source_file, stockage):
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

# ==============================================================================
    # GESTION DE LA CORBEILLE (CORRIGÉE AVEC LA MÉTHODE DE CONNEXION DU REPO)
    # ==============================================================================
    def ouvrirCorbeille(self):
        """ Récupère et affiche les documents supprimés lors des 15 derniers jours """
        import sqlite3
        from datetime import datetime, timedelta

        # 1. Calcul de la date limite (-15 jours par rapport à aujourd'hui)
        date_limite = datetime.now() - timedelta(days=15)
        # Format standard pour la base de données (ex: '2026-06-03')
        date_limite_str = date_limite.strftime("%Y-%m-%d")
        
        documents_supprimes = []
        
        try:
            # 2. Utilisation de la méthode de connexion interne de ton repo (_connect())
            conn = self.logic.repo._connect()
            conn.row_factory = sqlite3.Row  # Permet de lire les colonnes par nom
            cursor = conn.cursor()
            
            # 3. Exécution de la requête SQL pour récupérer les fichiers effacés
            # On tente d'abord avec les colonnes standards de date
            try:
                cursor.execute("""
                    SELECT * FROM Documents 
                    WHERE is_deleted = 1 
                    AND deleted_at >= ?
                """, (date_limite_str,))
                rows = cursor.fetchall()
            except sqlite3.OperationalError:
                # Sécurité : Si ta table utilise d'autres noms (comme 'supprime')
                # on récupère tous les éléments supprimés pour ne rien bloquer
                cursor.execute("SELECT * FROM Documents WHERE supprime = 1")
                rows = cursor.fetchall()
                
            # 4. Conversion des lignes SQL en dictionnaires pour l'interface
            for row in rows:
                documents_supprimes.append(dict(row))
                
            # 5. Fermeture de la connexion
            conn.close()
            
        except Exception as exc:
            QMessageBox.critical(self, "Erreur Corbeille", f"Impossible d'interroger la base de données : {exc}")
            return

        # 6. Mise à jour de l'affichage de l'application
        self.accueil_container.hide()
        self.left_container.show()
        self.right_panel.show()
        
        # 7. On vide le tableau avant de le remplir
        self.table.setRowCount(0)
        
        if not documents_supprimes:
            self.statusBar().showMessage("La corbeille est vide pour les 15 derniers jours.", 5000)
            return

        # 8. Remplissage du tableau avec les fichiers trouvés
        for document in documents_supprimes:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Récupération propre de la catégorie
            categories = document.get("categorie") or "-"
            if isinstance(categories, list):
                categories = ", ".join(categories)
                
            # Construction de la ligne du tableau
            valeurs = [
                f"[Supprimé] {document.get('titre', 'Sans titre')}",
                document.get("auteur", "Inconnu"),
                document.get("date_document") or document.get("date", "-"),
                categories,
            ]

            # Injection dans les cellules avec un style visuel rouge brique
            for col, valeur in enumerate(valeurs):
                item = QTableWidgetItem(str(valeur))
                item.setData(Qt.ItemDataRole.UserRole, document)  # Garde le dictionnaire en mémoire
                item.setForeground(QColor("#c0392b"))             # Écriture en rouge
                self.table.setItem(row, col, item)
                
        self.statusBar().showMessage(f"Corbeille : {len(documents_supprimes)} document(s) affiché(s).", 5000)

    def ouvrirContact(self):
        dialog = ContactDialog(self)
        dialog.exec()

    def ouvrirDocumentSelectionne(self):
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
        file_path = self.cheminDocumentSelectionne()
        if not file_path or not file_path.exists():
            QMessageBox.warning(self, "Erreur", "Fichier introuvable sur le disque.")
            return
        dest_path, _ = QFileDialog.getSaveFileName(self, "Enregistrer sous", file_path.name)
        if dest_path:
            shutil.copy(file_path, dest_path)
            QMessageBox.information(self, "Succès", "Fichier téléchargé/copié avec succès.")

    def createActions(self):
        # CORRECTION : Liaison de l'action Corbeille à la nouvelle fonction
        self.actArchive = QAction("&Corbeille", self)
        self.actArchive.setShortcut("Ctrl+A")
        self.actArchive.triggered.connect(self.ouvrirCorbeille)
        
        self.actPref = QAction("&Préférences", self)
        self.actPref.setShortcut("Ctrl+P")
        self.actPref.triggered.connect(self.ouvrirPreferences)
        self.actExit = QAction("Quitter", self)
        self.actExit.setShortcut("Alt+F4")
        self.actExit.triggered.connect(self.quitApp)
        self.actDelete = QAction("&Supprimer", self)
        self.actDelete.setShortcut("Ctrl+D")
        self.actDelete.triggered.connect(self.deleteDocument)
        self.actImport = QAction("&Sélectionner...", self)
        self.actImport.setShortcut("Ctrl+O")
        self.actImport.triggered.connect(self.importDocument)
        self.actGuide = QAction("&Guide", self)
        self.actGuide.setShortcut("Ctrl+G")
        self.actContact = QAction("&Contacter", self)
        # Changement du raccourci pour éviter le conflit avec Ctrl+A de la corbeille
        self.actContact.setShortcut("Ctrl+C") 
        self.actContact.triggered.connect(self.ouvrirContact)

    def createMenuBar(self):
        menu = self.menuBar()
        file = menu.addMenu("&Fichier")
        file.addAction(self.actArchive)
        file.addSeparator()
        file.addAction(self.actPref)
        file.addSeparator()
        file.addAction(self.actExit)

        edition = menu.addMenu("&Édition")
        edition.addAction(self.actDelete)

        import_menu = menu.addMenu("&Importer")
        import_menu.addAction(self.actImport)

        help_menu = menu.addMenu("&Aide")
        help_menu.addAction(self.actGuide)
        help_menu.addSeparator()
        help_menu.addAction(self.actContact)

    def quitApp(self):
        self.close()

    def deleteDocument(self):
        document = self.documentSelectionne()
        if not document:
            QMessageBox.warning(self, "Attention", "Veuillez cliquer sur une ligne du tableau d'abord.")
            return
        document_id = document.get("id")
        if not document_id:
            QMessageBox.warning(self, "Erreur", "Impossible d'identifier le document sélectionné.")
            return

        confirm = QMessageBox.question(
            self, "Confirmation",
            "Voulez-vous vraiment supprimer ce document ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.logic.delete_document(int(document_id))
                self.chargerDocuments()
                self.info_titre.setText("Titre : -")
                self.info_auteur.setText("Auteur : -")
                self.info_date.setText("Date : -")
                self.info_cat.setText("Catégorie : -")
                self.desc_box.clear()
            except Exception as exc:
                QMessageBox.critical(self, "Erreur", f"Impossible de supprimer le document : {exc}")

    def forcer_maj_polices_widgets(self, taille):
        f = self.font()
        f.setPointSize(taille)
        self.table.setFont(f)
        self.table.horizontalHeader().setFont(f)
        self.desc_box.setFont(f)
        self.info_titre.setFont(f)
        self.info_auteur.setFont(f)
        self.info_date.setFont(f)
        self.info_cat.setFont(f)
        self.search_bar.setFont(f)
        
        self.label_desc_title.setFont(f)
        f_bold = self.label_desc_title.font()
        f_bold.setBold(True)
        self.label_desc_title.setFont(f_bold)

    def ouvrirPreferences(self):
        app = QApplication.instance()
        taille_actuelle = app.font().pointSize()
        
        dialog = SowedropPreferencesDialog(self, actuel_theme=self.actuelle_theme, actuelle_taille=taille_actuelle)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.radio_sombre.isChecked():
                self.actuelle_theme = "Sombre"
                self.appliquer_theme_sombre()
            else:
                self.actuelle_theme = "Clair"
                self.appliquer_theme_clair()
                
            taille_choisie = dialog.spin_font.value()
            f = app.font()
            f.setPointSize(taille_choisie)
            app.setFont(f)
            self.forcer_maj_polices_widgets(taille_choisie)
                
            self.statusBar().showMessage("Préférences enregistrées.", 3000)

    # ==============================================================================
    # FEUILLES DE STYLE CSS (BOUTONS RADIO CORRIGÉS POUR APPARETRE NETTEMENT)
    # ==============================================================================
    def appliquer_theme_sombre(self):
        theme_sombre = """
            QMainWindow, QDialog { background-color: #121212; color: #ffffff; }
            QLabel { color: #ffffff; }
            #welcomeLabel { font-size: 26px; font-weight: bold; margin-top: 15px; margin-bottom: 25px; color: #e67e22; }
            QMenuBar { background-color: #1e1e1e; color: #ffffff; border-bottom: 1px solid #e67e22; }
            QMenuBar::item:selected { background-color: #e67e22; color: #ffffff; }
            QMenu { background-color: #1e1e1e; color: #ffffff; border: 1px solid #e67e22; }
            QMenu::item:selected { background-color: #e67e22; color: #ffffff; }
            
            QTableWidget { background-color: #1e1e1e; color: #ffffff; gridline-color: #444444; border: 1px solid #333; }
            QHeaderView::section { background-color: #2d2d30; color: #e67e22; border: 1px solid #444444; padding: 5px; font-weight: bold; }
            QTableWidget::item:selected { background-color: #e67e22; color: #ffffff; }
            
            QLineEdit, QTextEdit, QSpinBox, QComboBox, QDateEdit { background-color: #1e1e1e; color: #ffffff; border: 1px solid #555; padding: 5px; border-radius: 4px; }
            QComboBox QAbstractItemView { background-color: #1e1e1e; color: #ffffff; border: 1px solid #555; selection-background-color: #e67e22; selection-color: #ffffff; }
            #searchBarAccueil { padding: 12px; font-size: 15px; border-radius: 6px; background-color: #1e1e1e; color: #ffffff; border: 1px solid #e67e22; }
            
            #rightPanel { border-left: 1px solid #e67e22; }
            QPushButton { background-color: #e67e22; color: #ffffff; border: 1px solid #d35400; padding: 6px 12px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #d35400; }
            
            /* BOUTONS RADIO SOMBRES : Texte blanc, fond clair automatique pour la puce native */
            QRadioButton { color: #ffffff; font-weight: bold; padding: 4px; }
        """
        self.setStyleSheet(theme_sombre)

    def appliquer_theme_clair(self):
        theme_clair = """
            QMainWindow, QDialog { background-color: #fdfdfd; color: #000000; }
            QLabel { color: #000000; }
            #welcomeLabel { font-size: 26px; font-weight: bold; margin-top: 15px; margin-bottom: 25px; color: #e67e22; }
            QMenuBar { background-color: #ffffff; color: #000000; border-bottom: 1px solid #f5cba7; }
            QMenuBar::item:selected { background-color: #fdebd0; color: #e67e22; }
            QMenu { background-color: #ffffff; color: #000000; border: 1px solid #f5cba7; }
            QMenu::item:selected { background-color: #e67e22; color: #ffffff; }
            
            QTableWidget { background-color: #ffffff; color: #000000; gridline-color: #f5cba7; border: 1px solid #f5cba7; }
            QHeaderView::section { background-color: #fdebd0; color: #e67e22; border: 1px solid #f5cba7; padding: 5px; font-weight: bold; }
            QTableWidget::item:selected { background-color: #e67e22; color: #ffffff; }
            
            QLineEdit, QTextEdit, QSpinBox, QComboBox, QDateEdit { background-color: #ffffff; color: #000000; border: 1px solid #f5cba7; padding: 5px; border-radius: 4px; }
            QComboBox QAbstractItemView { background-color: #ffffff; color: #000000; border: 1px solid #f5cba7; selection-background-color: #e67e22; selection-color: #ffffff; }
            #searchBarAccueil { padding: 12px; font-size: 15px; border-radius: 6px; background-color: #ffffff; color: #000000; border: 1px solid #e67e22; }
            
            #rightPanel { border-left: 1px solid #f5cba7; }
            QPushButton { background-color: #fdebd0; color: #e67e22; border: 1px solid #e67e22; padding: 6px 12px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #e67e22; color: #ffffff; }
            
            /* BOUTONS RADIO CLAIRS : Texte noir, puce native parfaitement visible */
            QRadioButton { color: #000000; font-weight: bold; padding: 4px; }
        """
        self.setStyleSheet(theme_clair)