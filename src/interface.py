import os
import platform
import shutil
import sqlite3
import subprocess
from pathlib import Path

# Logique de base et signaux
from PyQt6.QtCore import QDate, QEvent, Qt, QTimer
# Pour le visuel
from PyQt6.QtGui import QAction, QColor, QIcon, QPixmap, QStandardItem, QStandardItemModel
# Éléments d'interface
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.database import build_repository
from src.logic import DocumentInput, LogicService, SearchFilters, ValidationError
from src.sftp_storage import SftpStorage, SftpStorageError, is_sftp_resource


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
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Enregistrer")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)


def trouver_logo():
    candidats = [
        "./assets/icons/logo.webp",
        "./assets/icons/logo.png",
        "pouce.png",
        "pouce.webp",
        "pouce.jpg",
        "pouce.jpeg",
    ]
    for chemin in candidats:
        if os.path.exists(chemin):
            return chemin
    return "./assets/icons/logo.webp"


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
            logo_lbl.setPixmap(
                pixmap.scaled(
                    90,
                    90,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        layout.addWidget(logo_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Support SoweDrop")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 10px; margin-bottom: 10px;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        info = QLabel(
            "Une question ou un bug ?\n\n"
            "📧 Contact : support@sowedrop.com\n"
            "🌐 Site officiel : https://heloweeze.github.io/SoweDrop/\n\n"
            "Version 1.0.0 (3 juin 2026)"
        )
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

    def clear_checked_items(self):
        for row in range(self._items_model.rowCount()):
            item = self._items_model.item(row)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)
        self._update_display_text()

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

        # Mots-clés : liste de termes séparés par des points-virgules
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

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
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
        super().__init__()

        self.project_root = Path(project_root or Path(__file__).resolve().parent.parent)
        self.logic = logic_service or LogicService(build_repository(self.project_root))

        self.setWindowTitle("SoweDrop")
        self.setWindowIcon(QIcon(trouver_logo()))
        self.resize(1100, 700)

        self.actuelle_theme = "Clair"

        # Création des actions et des menus avant d'afficher le contenu principal
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
        pixmap = QPixmap(trouver_logo())
        if not pixmap.isNull():
            self.logo_label.setPixmap(
                pixmap.scaled(
                    130,
                    130,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
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

        self.creerFiltresRecherche(self.left_layout)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Titre", "Auteur", "Date", "Catégorie"])
        # La sélection se fait sur toute la ligne pour manipuler un document complet
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)

        self.left_layout.addWidget(self.table)

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
        self.info_ressource = QLabel("Ressource : -")
        self.info_mots_cles = QLabel("Mots-clés : -")
        self.info_ressource.setWordWrap(True)
        self.info_mots_cles.setWordWrap(True)

        # Labels pour les infos : ils restent en attributs self pour être mis à jour
        for label in [
            self.info_titre,
            self.info_auteur,
            self.info_date,
            self.info_cat,
            self.info_ressource,
            self.info_mots_cles,
        ]:
            self.right_layout.addWidget(label)

        self.label_desc_title = QLabel("Description :")
        f_desc = self.label_desc_title.font()
        f_desc.setBold(True)
        self.label_desc_title.setFont(f_desc)
        self.right_layout.addWidget(self.label_desc_title)

        self.desc_box = QTextEdit()
        self.desc_box.setReadOnly(True)
        self.right_layout.addWidget(self.desc_box)
        self.right_layout.addStretch()

        # Layout horizontal pour les boutons côte à côte
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

        # Connexions des interactions principales
        self.table.itemClicked.connect(self.afficherDetails)
        self.table.customContextMenuRequested.connect(self.afficherMenuContextuelDocument)
        self.btn_ouvrir.clicked.connect(self.ouvrirDocumentSelectionne)
        self.btn_telecharger.clicked.connect(self.telechargerDocument)

        self.afficherTableauVide()
        self.appliquer_theme_clair()

        # Synchronisation silencieuse au démarrage : si la config SFTP est absente
        # ou si le réseau est indisponible, on ne bloque pas l'application.
        QTimer.singleShot(500, lambda: self.synchroniserDocumentsPartages(afficher_message=False))

    def afficherInterfaceDocuments(self):
        # Cache l'accueil et affiche l'interface classique avec le tableau
        self.accueil_container.hide()
        self.left_container.show()
        self.right_panel.show()

    def executer_recherche_accueil(self):
        # Recherche lancée depuis la page d'accueil
        texte_saisi = self.search_bar_accueil.text().strip()
        self.afficherInterfaceDocuments()
        self.search_titre.setText(texte_saisi)
        self.rechercherDocuments()
        self.search_titre.setFocus()

    def afficherMenuContextuelDocument(self, position):
        # Affiche le menu clic droit à l'endroit demandé dans le tableau
        menu = self.creerMenuContextuelDocument(position)
        menu.exec(self.table.viewport().mapToGlobal(position))

    def creerMenuContextuelDocument(self, position):
        index = self.table.indexAt(position)
        menu = QMenu(self)

        if index.isValid():
            # Si le clic est sur une ligne, on sélectionne le document correspondant
            self.table.selectRow(index.row())
            self.afficherDetails(self.table.item(index.row(), 0))

            action_ouvrir = menu.addAction("Ouvrir")
            action_telecharger = menu.addAction("Télécharger")
            action_supprimer = menu.addAction("Supprimer")
            action_copier_ressource = menu.addAction("Copier le chemin de la ressource")

            action_ouvrir.triggered.connect(self.ouvrirDocumentSelectionne)
            action_telecharger.triggered.connect(self.telechargerDocument)
            action_supprimer.triggered.connect(self.deleteDocument)
            action_copier_ressource.triggered.connect(self.copierCheminRessourceSelectionne)
            menu.addSeparator()
        else:
            # Si le clic est hors document, on vide la sélection et les détails
            self.table.clearSelection()
            self.table.setCurrentCell(-1, -1)
            self.viderDetails()

        action_ajouter = menu.addAction("Ajouter un document")
        action_ajouter.triggered.connect(self.importDocument)
        return menu

    def creerFiltresRecherche(self, parent_layout):
        parent_layout.addWidget(QLabel("Recherche multicritère"))

        # Première ligne : recherche par titre, auteur et mots-clés
        ligne_principale = QHBoxLayout()
        self.search_titre = QLineEdit()
        self.search_titre.setPlaceholderText("Titre")
        self.search_auteur = QLineEdit()
        self.search_auteur.setPlaceholderText("Auteur")
        self.search_mots_cles = QLineEdit()
        self.search_mots_cles.setPlaceholderText("Mots-clés, séparés par virgules")
        ligne_principale.addWidget(self.search_titre)
        ligne_principale.addWidget(self.search_auteur)
        ligne_principale.addWidget(self.search_mots_cles)
        parent_layout.addLayout(ligne_principale)

        # Deuxième ligne : choix des catégories avec cases à cocher
        ligne_secondaire = QHBoxLayout()
        self.search_categories = CheckableComboBox("Toutes les catégories")
        self.search_categories.add_checkable_items(self.logic.list_categories())
        ligne_secondaire.addWidget(self.search_categories)
        parent_layout.addLayout(ligne_secondaire)

        # Troisième ligne : filtres de dates et boutons de recherche
        ligne_dates = QHBoxLayout()
        self.search_date_min_active = QCheckBox("Date min")
        self.search_date_min = QDateEdit(QDate.currentDate().addYears(-1))
        self.search_date_min.setCalendarPopup(True)
        self.search_date_min.setDisplayFormat("yyyy-MM-dd")
        self.search_date_min.setEnabled(False)

        self.search_date_max_active = QCheckBox("Date max")
        self.search_date_max = QDateEdit(QDate.currentDate())
        self.search_date_max.setCalendarPopup(True)
        self.search_date_max.setDisplayFormat("yyyy-MM-dd")
        self.search_date_max.setEnabled(False)

        self.btn_rechercher = QPushButton("Rechercher")
        self.btn_reset_search = QPushButton("Réinitialiser")

        ligne_dates.addWidget(self.search_date_min_active)
        ligne_dates.addWidget(self.search_date_min)
        ligne_dates.addWidget(self.search_date_max_active)
        ligne_dates.addWidget(self.search_date_max)
        ligne_dates.addStretch()
        ligne_dates.addWidget(self.btn_rechercher)
        ligne_dates.addWidget(self.btn_reset_search)
        parent_layout.addLayout(ligne_dates)

        # Dernière ligne : paramètres de tri des résultats
        ligne_tri = QHBoxLayout()
        ligne_tri.addWidget(QLabel("Trier par :"))
        self.search_sort_by = QComboBox()
        self.search_sort_by.addItem("Date", "date")
        self.search_sort_by.addItem("Titre", "titre")
        self.search_sort_by.addItem("Auteur", "auteur")

        self.search_sort_order = QComboBox()
        self.search_sort_order.addItem("Décroissant", "desc")
        self.search_sort_order.addItem("Croissant", "asc")

        ligne_tri.addWidget(self.search_sort_by)
        ligne_tri.addWidget(QLabel("Ordre :"))
        ligne_tri.addWidget(self.search_sort_order)
        ligne_tri.addStretch()
        parent_layout.addLayout(ligne_tri)

        # Connexions des champs de recherche
        self.search_date_min_active.toggled.connect(self.search_date_min.setEnabled)
        self.search_date_max_active.toggled.connect(self.search_date_max.setEnabled)
        self.btn_rechercher.clicked.connect(self.rechercherDocuments)
        self.btn_reset_search.clicked.connect(self.reinitialiserRecherche)
        self.search_sort_by.currentIndexChanged.connect(self.rechercherDocuments)
        self.search_sort_order.currentIndexChanged.connect(self.rechercherDocuments)

        for champ in (self.search_titre, self.search_auteur, self.search_mots_cles):
            champ.returnPressed.connect(self.rechercherDocuments)

    def chargerDocuments(self):
        # Récupère tous les documents via la couche logique puis les affiche
        self.chargerDocumentsAvecFiltres(SearchFilters())

    def afficherTableauVide(self):
        self.afficherDocuments([])

    def chargerDocumentsAvecFiltres(self, filters, afficher_message_aucun=False):
        try:
            documents = self.logic.search_documents(filters)
            self.afficherDocuments(documents)
            if afficher_message_aucun and not documents:
                QMessageBox.information(self, "Recherche", "Aucun document trouvé")
        except ValidationError as exc:
            QMessageBox.warning(self, "Validation", str(exc))
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible de charger les documents : {exc}")

    def afficherDocuments(self, documents):
        # On vide le tableau avant de le remplir avec les documents reçus
        self.table.setRowCount(0)
        self.table.clearSelection()
        self.viderDetails()

        for document in documents:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Construction de la ligne du tableau
            categories = ", ".join(document.get("categorie") or []) or "-"
            valeurs = [
                document.get("titre", ""),
                document.get("auteur", ""),
                document.get("date", ""),
                categories,
            ]

            for col, valeur in enumerate(valeurs):
                item = QTableWidgetItem(str(valeur))
                # Garde le dictionnaire complet en mémoire dans la cellule
                item.setData(Qt.ItemDataRole.UserRole, document)
                self.table.setItem(row, col, item)

    def construireFiltresRecherche(self):
        # Transforme les champs de l'interface en filtres exploitables par la logique
        return SearchFilters(
            titre=self.search_titre.text(),
            auteur=self.search_auteur.text(),
            categories=self.search_categories.checked_items(),
            mots_cles=self.search_mots_cles.text(),
            date_min=(
                self.search_date_min.date().toString("yyyy-MM-dd")
                if self.search_date_min_active.isChecked()
                else None
            ),
            date_max=(
                self.search_date_max.date().toString("yyyy-MM-dd")
                if self.search_date_max_active.isChecked()
                else None
            ),
            sort_by=self.search_sort_by.currentData(),
            sort_order=self.search_sort_order.currentData(),
        )

    def rechercherDocuments(self):
        self.afficherInterfaceDocuments()
        self.chargerDocumentsAvecFiltres(
            self.construireFiltresRecherche(),
            afficher_message_aucun=True,
        )

    def reinitialiserRecherche(self):
        # Remet tous les champs de recherche et de tri à leur état initial
        self.search_titre.clear()
        self.search_auteur.clear()
        self.search_mots_cles.clear()
        self.search_categories.clear_checked_items()
        self.search_date_min_active.setChecked(False)
        self.search_date_max_active.setChecked(False)
        self.search_date_min.setEnabled(False)
        self.search_date_max.setEnabled(False)

        sort_by_was_blocked = self.search_sort_by.blockSignals(True)
        sort_order_was_blocked = self.search_sort_order.blockSignals(True)
        self.search_sort_by.setCurrentIndex(0)
        self.search_sort_order.setCurrentIndex(0)
        self.search_sort_by.blockSignals(sort_by_was_blocked)
        self.search_sort_order.blockSignals(sort_order_was_blocked)

        self.afficherTableauVide()

    def viderDetails(self):
        # Remet la fiche détails dans son état vide
        self.info_titre.setText("Titre : -")
        self.info_auteur.setText("Auteur : -")
        self.info_date.setText("Date : -")
        self.info_cat.setText("Catégorie : -")
        self.info_ressource.setText("Ressource : -")
        self.info_mots_cles.setText("Mots-clés : -")
        self.desc_box.clear()

    def documentSelectionne(self):
        # Retourne le document complet associé à la ligne sélectionnée
        current_row = self.table.currentRow()
        if current_row == -1:
            return None
        item = self.table.item(current_row, 0)
        if not item:
            return None
        document = item.data(Qt.ItemDataRole.UserRole)
        return document if isinstance(document, dict) else None

    def cheminDocumentSelectionne(self):
        """
        Retourne un chemin local utilisable par l'application.

        Si la ressource est SFTP, le fichier est d'abord téléchargé dans
        data/documents/cache/ puis ce chemin local est retourné.
        """
        document = self.documentSelectionne()
        if not document:
            return None
        ressource = document.get("chemin_fichier") or document.get("ressource")
        if not ressource:
            return None

        if is_sftp_resource(ressource):
            remote_path = ressource.replace("sftp:", "", 1)
            filename = Path(remote_path).name
            cache_dir = self.project_root / "data" / "documents" / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            local_cache_path = cache_dir / filename

            sftp_storage = SftpStorage.from_project(self.project_root)
            sftp_storage.download_file(ressource, local_cache_path)
            return local_cache_path

        chemin = Path(ressource)
        if not chemin.is_absolute():
            chemin = self.project_root / chemin

        legacy_data_path = self.project_root / "data" / ressource
        if not chemin.exists() and legacy_data_path.exists():
            chemin = legacy_data_path

        return chemin

    def copierCheminRessourceSelectionne(self):
        # Copie le chemin du document dans le presse-papiers
        document = self.documentSelectionne()
        if not document:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner un document.")
            return

        ressource = document.get("ressource") or document.get("chemin_fichier")
        if not ressource:
            QMessageBox.warning(self, "Erreur", "Aucun chemin de ressource disponible.")
            return

        QApplication.clipboard().setText(str(ressource))
        self.statusBar().showMessage("Chemin de la ressource copié", 3000)

    def afficherDetails(self, item):
        # Affiche les informations principales du document sélectionné
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
        # On va chercher les informations supplémentaires associées au document
        ressource = document.get("ressource") if document else ""
        mots_cles = ", ".join(document.get("mots_cles") or []) if document else ""
        description = document.get("description") if document else ""

        self.info_ressource.setText(f"Ressource : {ressource or '-'}")
        self.info_mots_cles.setText(f"Mots-clés : {mots_cles or '-'}")
        self.desc_box.setText(description or f"Aucune description pour : {titre}")

    def filtrerTableau(self):
        self.rechercherDocuments()

    def importDocument(self):
        # Ouvre la boîte de dialogue d'import et enregistre le document en base
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

                # Préparation de l'objet métier envoyé à la couche logique
                suffix = Path(data["fichier"]).suffix.upper().lstrip(".")

                document_input = DocumentInput(
                    titre=data["titre"],
                    auteur=data["auteur"],
                    date_document=data["date"],
                    ressource=relative_resource,
                    description=data["description"],
                    categories=data["categories"],
                    mots_cles=data["mots_cles"],
                    stockage=data["stockage"],
                    chemin_fichier=relative_resource,
                    type_fichier=suffix,
                )

                document_id = self.logic.add_document(document_input)

                # Si le document est partagé, on publie aussi ses métadonnées sur le VPS
                if data["stockage"] == "partage" and is_sftp_resource(relative_resource):
                    self.publierMetadonneesDocumentPartage(
                        document_input=document_input,
                        document_id=document_id,
                    )

                QMessageBox.information(
                    self,
                    "Ajout",
                    f"Document ajouté avec succès (id {document_id}).",
                )
                self.afficherInterfaceDocuments()
                self.chargerDocuments()

            except ValidationError as exc:
                QMessageBox.warning(self, "Validation", str(exc))
            except SftpStorageError as exc:
                QMessageBox.critical(self, "Erreur SFTP", str(exc))
            except Exception as exc:
                QMessageBox.critical(self, "Erreur", f"Impossible d'ajouter le document : {exc}")

    def copierFichierDansStockage(self, source_file, stockage):
        """
        Copie le fichier choisi dans le bon espace de stockage.

        - local : copie dans data/documents/local/
        - partage : upload sur le VPS en SFTP dans /commun
        """
        source = Path(source_file)

        if stockage == "partage":
            sftp_storage = SftpStorage.from_project(self.project_root)
            return sftp_storage.upload_file(source)

        target_dir = self.project_root / "data" / "documents" / stockage
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

    def publierMetadonneesDocumentPartage(self, document_input: DocumentInput, document_id: int) -> str:
        """Publie un fichier JSON de métadonnées à côté du fichier partagé."""
        metadata = {
            "sync_version": 1,
            "source_app": "SoweDrop",
            "source_document_id": document_id,
            "titre": document_input.titre,
            "auteur": document_input.auteur,
            "date_document": str(document_input.date_document),
            "ressource": document_input.ressource,
            "description": document_input.description,
            "categories": document_input.categories,
            "mots_cles": document_input.mots_cles,
            "stockage": "partage",
            "chemin_fichier": document_input.chemin_fichier or document_input.ressource,
            "type_fichier": document_input.type_fichier,
        }

        sftp_storage = SftpStorage.from_project(self.project_root)
        return sftp_storage.upload_metadata(metadata, document_input.ressource)

    def synchroniserDocumentsPartages(self, afficher_message=True):
        """
        Synchronise la base SQLite locale avec les documents partagés du SFTP.

        Le SFTP contient les fichiers réels + un fichier .json de métadonnées
        pour chaque document partagé. Cette méthode lit ces JSON et ajoute
        dans la base locale les documents absents.
        """
        try:
            sftp_storage = SftpStorage.from_project(self.project_root)
            metadata_list = sftp_storage.list_metadata()

            documents_locaux = self.logic.search_documents(SearchFilters())
            # Ressources déjà connues localement : évite les doublons à la synchronisation
            ressources_connues = {
                str(doc.get("ressource") or doc.get("chemin_fichier") or "")
                for doc in documents_locaux
            }

            ajoutes = 0
            ignores = 0
            erreurs = []

            for metadata in metadata_list:
                # Chaque fichier .json distant décrit un document partagé
                ressource = str(metadata.get("ressource") or metadata.get("chemin_fichier") or "").strip()

                if not ressource or not is_sftp_resource(ressource):
                    ignores += 1
                    continue

                if ressource in ressources_connues:
                    ignores += 1
                    continue

                try:
                    # Si le type de fichier n'est pas indiqué, on le déduit de l'extension
                    type_fichier = str(metadata.get("type_fichier") or "").strip()
                    if not type_fichier:
                        type_fichier = Path(ressource.replace("sftp:", "", 1)).suffix.upper().lstrip(".")

                    document_id = self.logic.add_document(
                        DocumentInput(
                            titre=str(metadata.get("titre") or Path(ressource).stem),
                            auteur=str(metadata.get("auteur") or "Utilisateur distant"),
                            date_document=str(metadata.get("date_document") or metadata.get("date") or "2026-01-01"),
                            ressource=ressource,
                            description=str(metadata.get("description") or ""),
                            categories=list(metadata.get("categories") or []),
                            mots_cles=list(metadata.get("mots_cles") or []),
                            stockage="partage",
                            chemin_fichier=ressource,
                            type_fichier=type_fichier,
                        )
                    )
                    ressources_connues.add(ressource)
                    ajoutes += 1
                    self.logic.repository.add_history(document_id, "Synchronisation depuis le SFTP")
                except Exception as exc:
                    erreurs.append(f"{ressource} : {exc}")

            if ajoutes:
                self.afficherInterfaceDocuments()
                self.chargerDocuments()

            if afficher_message:
                message = (
                    f"Synchronisation terminée.\n\n"
                    f"Documents ajoutés : {ajoutes}\n"
                    f"Documents déjà connus/ignorés : {ignores}"
                )
                if erreurs:
                    message += "\n\nErreurs :\n" + "\n".join(erreurs[:5])
                    if len(erreurs) > 5:
                        message += f"\n... et {len(erreurs) - 5} autre(s) erreur(s)."
                    QMessageBox.warning(self, "Synchronisation partielle", message)
                else:
                    QMessageBox.information(self, "Synchronisation", message)

            return ajoutes

        except SftpStorageError as exc:
            if afficher_message:
                QMessageBox.critical(self, "Erreur SFTP", str(exc))
            return 0
        except Exception as exc:
            if afficher_message:
                QMessageBox.critical(self, "Erreur", f"Synchronisation impossible : {exc}")
            return 0

    def ouvrirCorbeille(self):
        """Affiche les documents marqués comme supprimés dans la base."""
        documents_supprimes = []

        try:
            # Utilisation de la méthode de connexion interne du repository
            conn = self.logic.repository._connect()
            conn.row_factory = sqlite3.Row
            # Requête SQL pour récupérer les documents au statut supprimé
            rows = conn.execute(
                """
                SELECT
                    d.idDoc,
                    d.titre,
                    d.description,
                    d.date_document,
                    d.ressource,
                    d.type_fichier,
                    d.stockage,
                    d.statut,
                    d.idUser,
                    u.nom AS auteur_nom,
                    u.prenom AS auteur_prenom,
                    u.matricule AS auteur_matricule
                FROM Documents d
                JOIN Utilisateurs u ON u.idUser = d.idUser
                WHERE d.statut = 'supprime'
                ORDER BY d.idDoc DESC
                """
            ).fetchall()

            # Conversion des lignes SQL en dictionnaires pour l'interface
            for row in rows:
                documents_supprimes.append(self.logic._format_document_result(dict(row)))

            # Fermeture de la connexion
            conn.close()

        except Exception as exc:
            QMessageBox.critical(self, "Erreur Corbeille", f"Impossible d'interroger la base de données : {exc}")
            return

        # Mise à jour de l'affichage de l'application
        self.afficherInterfaceDocuments()
        # On vide le tableau avant de le remplir avec les documents supprimés
        self.table.setRowCount(0)

        if not documents_supprimes:
            self.statusBar().showMessage("La corbeille est vide.", 5000)
            return

        for document in documents_supprimes:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Récupération propre de la catégorie
            categories = document.get("categorie") or "-"
            if isinstance(categories, list):
                categories = ", ".join(categories) or "-"

            valeurs = [
                f"[Supprimé] {document.get('titre', 'Sans titre')}",
                document.get("auteur", "Inconnu"),
                document.get("date") or "-",
                categories,
            ]

            # Injection dans les cellules avec un style visuel rouge brique
            for col, valeur in enumerate(valeurs):
                item = QTableWidgetItem(str(valeur))
                item.setData(Qt.ItemDataRole.UserRole, document)
                item.setForeground(QColor("#c0392b"))
                self.table.setItem(row, col, item)

        self.statusBar().showMessage(f"Corbeille : {len(documents_supprimes)} document(s) affiché(s).", 5000)

    def ouvrirContact(self):
        dialog = ContactDialog(self)
        dialog.exec()

    def ouvrirDocumentSelectionne(self):
        # Ouvre le fichier du document sélectionné avec l'application système
        try:
            file_path = self.cheminDocumentSelectionne()
        except SftpStorageError as exc:
            QMessageBox.critical(self, "Erreur SFTP", str(exc))
            return

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
        # Copie le document sélectionné vers l'emplacement choisi par l'utilisateur
        try:
            file_path = self.cheminDocumentSelectionne()
        except SftpStorageError as exc:
            QMessageBox.critical(self, "Erreur SFTP", str(exc))
            return

        if not file_path or not file_path.exists():
            QMessageBox.warning(self, "Erreur", "Fichier introuvable sur le disque.")
            return

        dest_path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer sous",
            file_path.name,
        )
        if dest_path:
            shutil.copy(file_path, dest_path)
            QMessageBox.information(self, "Succès", "Fichier téléchargé/copié avec succès.")

    def createActions(self):
        # Partie Fichier
        # Corbeille : endroit où les documents récemment supprimés se trouvent
        self.actArchive = QAction("&Corbeille", self)
        self.actArchive.setShortcut("Ctrl+A")
        self.actArchive.setStatusTip("Archive des documents récemment effacés")
        self.actArchive.triggered.connect(self.ouvrirCorbeille)

        # Préférences : fenêtre pour changer l'apparence de l'appli
        self.actPref = QAction("&Préférences", self)
        self.actPref.setShortcut("Ctrl+P")
        self.actPref.triggered.connect(self.ouvrirPreferences)

        # Quitter l'application
        self.actExit = QAction("Quitter", self)
        self.actExit.setShortcut("Alt+F4")
        self.actExit.triggered.connect(self.quitApp)

        # Exporter : sauvegarde le tableau actuel dans un fichier texte
        self.actExport = QAction("&Exporter", self)
        self.actExport.setShortcut("Ctrl+E")
        self.actExport.setStatusTip("Exporter le tableau")
        self.actExport.triggered.connect(self.exportDocument)

        # Supprimer : envoie le document sélectionné dans la corbeille
        self.actDelete = QAction("&Supprimer", self)
        self.actDelete.setShortcut("Ctrl+D")
        self.actDelete.triggered.connect(self.deleteDocument)

        # Importer : ouvre la fenêtre d'ajout d'un nouveau document
        self.actImport = QAction("&Sélectionner un document...", self)
        self.actImport.setShortcut("Ctrl+O")
        self.actImport.triggered.connect(self.importDocument)

        # Synchroniser : récupère les documents partagés depuis le SFTP
        self.actSyncPartage = QAction("&Synchroniser les documents partagés", self)
        self.actSyncPartage.setShortcut("Ctrl+R")
        self.actSyncPartage.setStatusTip("Récupérer depuis le SFTP les documents partagés absents de la base locale")
        self.actSyncPartage.triggered.connect(lambda: self.synchroniserDocumentsPartages(afficher_message=True))

        # Guide utilisateur
        self.actGuide = QAction("&Guide utilisateur", self)
        self.actGuide.setShortcut("Ctrl+G")
        self.actGuide.setStatusTip("Guide utilisateur")

        # Contact : affiche les informations pour joindre l'équipe
        self.actContact = QAction("&Contacter", self)
        self.actContact.setShortcut("Ctrl+M")
        self.actContact.setStatusTip("Contacter les développeurs")
        self.actContact.triggered.connect(self.ouvrirContact)

    def createMenuBar(self):
        menu = self.menuBar()

        # Partie Fichier
        file_menu = menu.addMenu("&Fichier")
        file_menu.addAction(self.actArchive)
        file_menu.addAction(self.actExport)
        file_menu.addSeparator()
        file_menu.addAction(self.actPref)
        file_menu.addSeparator()
        file_menu.addAction(self.actExit)

        # Partie Édition
        edition = menu.addMenu("&Édition")
        edition.addAction(self.actDelete)

        # Partie Importer
        import_menu = menu.addMenu("&Importer")
        import_menu.addAction(self.actImport)
        import_menu.addSeparator()
        import_menu.addAction(self.actSyncPartage)

        # Partie Aide
        help_menu = menu.addMenu("&Aide")
        help_menu.addAction(self.actGuide)
        help_menu.addSeparator()
        help_menu.addAction(self.actContact)

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
            "Fichier Texte (*.txt);;Tous les fichiers (*)",
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    for row in range(self.table.rowCount()):
                        # On parcourt les lignes et les colonnes
                        row_data = []
                        for col in range(self.table.columnCount()):
                            item = self.table.item(row, col)
                            # On récupère le texte ou un vide si la cellule est vide
                            row_data.append(item.text() if item else "")
                        # On écrit la ligne dans le fichier
                        f.write(" | ".join(row_data) + "\n")
            except Exception as exc:
                QMessageBox.critical(self, "Erreur", f"Impossible d'exporter : {exc}")

    def deleteDocument(self):
        # Suppression du document sélectionné après confirmation utilisateur
        document = self.documentSelectionne()
        if not document:
            QMessageBox.warning(self, "Attention", "Veuillez cliquer sur une ligne du tableau d'abord.")
            return
        document_id = document.get("id")
        if not document_id:
            QMessageBox.warning(self, "Erreur", "Impossible d'identifier le document sélectionné.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirmation",
            "Voulez-vous vraiment supprimer ce document ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            self.logic.delete_document(int(document_id))
            self.chargerDocuments()
            self.viderDetails()
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible de supprimer le document : {exc}")

    def forcer_maj_polices_widgets(self, taille):
        # Applique la nouvelle taille de police aux widgets principaux
        f = self.font()
        f.setPointSize(taille)

        for widget in [
            self.table,
            self.desc_box,
            self.info_titre,
            self.info_auteur,
            self.info_date,
            self.info_cat,
            self.info_ressource,
            self.info_mots_cles,
            self.search_titre,
            self.search_auteur,
            self.search_mots_cles,
            self.search_bar_accueil,
            self.label_desc_title,
        ]:
            widget.setFont(f)

        self.table.horizontalHeader().setFont(f)
        f_bold = self.label_desc_title.font()
        f_bold.setBold(True)
        self.label_desc_title.setFont(f_bold)

    def ouvrirPreferences(self):
        # Ouvre la fenêtre des préférences et applique les choix validés
        app = QApplication.instance()
        taille_actuelle = app.font().pointSize()

        dialog = SowedropPreferencesDialog(
            self,
            actuel_theme=self.actuelle_theme,
            actuelle_taille=taille_actuelle,
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.radio_sombre.isChecked():
                self.actuelle_theme = "Sombre"
                self.appliquer_theme_sombre()
            else:
                self.actuelle_theme = "Clair"
                self.appliquer_theme_clair()

            # Gestion de la taille de la police globale
            taille_choisie = dialog.spin_font.value()
            f = app.font()
            f.setPointSize(taille_choisie)
            app.setFont(f)
            self.forcer_maj_polices_widgets(taille_choisie)

            self.statusBar().showMessage("Préférences enregistrées.", 3000)

    def appliquer_theme_sombre(self):
        theme_sombre = """
            QMainWindow, QDialog { background-color: #121212; color: #ffffff; }
            QLabel, QCheckBox { color: #ffffff; }
            #welcomeLabel { font-size: 26px; font-weight: bold; margin-top: 15px; margin-bottom: 25px; color: #e67e22; }
            QMenuBar { background-color: #1e1e1e; color: #ffffff; border-bottom: 1px solid #e67e22; }
            QMenuBar::item:selected { background-color: #e67e22; color: #ffffff; }
            QMenu { background-color: #1e1e1e; color: #ffffff; border: 1px solid #e67e22; }
            QMenu::item:selected { background-color: #e67e22; color: #ffffff; }

            QTableWidget { background-color: #1e1e1e; color: #ffffff; gridline-color: #444444; border: 1px solid #333; }
            QHeaderView::section { background-color: #2d2d30; color: #e67e22; border: 1px solid #444444; padding: 5px; font-weight: bold; }
            QTableWidget::item:selected { background-color: #e67e22; color: #ffffff; }

            QLineEdit, QTextEdit, QSpinBox, QComboBox, QDateEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 4px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555;
                selection-background-color: #e67e22;
                selection-color: #ffffff;
            }
            #searchBarAccueil { padding: 12px; font-size: 15px; border-radius: 6px; background-color: #1e1e1e; color: #ffffff; border: 1px solid #e67e22; }

            #rightPanel { border-left: 1px solid #e67e22; }
            QPushButton { background-color: #e67e22; color: #ffffff; border: 1px solid #d35400; padding: 6px 12px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #d35400; }
            QRadioButton { color: #ffffff; font-weight: bold; padding: 4px; }
        """
        self.setStyleSheet(theme_sombre)

    def appliquer_theme_clair(self):
        theme_clair = """
            QMainWindow, QDialog { background-color: #fdfdfd; color: #000000; }
            QLabel, QCheckBox { color: #000000; }
            #welcomeLabel { font-size: 26px; font-weight: bold; margin-top: 15px; margin-bottom: 25px; color: #e67e22; }
            QMenuBar { background-color: #ffffff; color: #000000; border-bottom: 1px solid #f5cba7; }
            QMenuBar::item:selected { background-color: #fdebd0; color: #e67e22; }
            QMenu { background-color: #ffffff; color: #000000; border: 1px solid #f5cba7; }
            QMenu::item:selected { background-color: #e67e22; color: #ffffff; }

            QTableWidget { background-color: #ffffff; color: #000000; gridline-color: #f5cba7; border: 1px solid #f5cba7; }
            QHeaderView::section { background-color: #fdebd0; color: #e67e22; border: 1px solid #f5cba7; padding: 5px; font-weight: bold; }
            QTableWidget::item:selected { background-color: #e67e22; color: #ffffff; }

            QLineEdit, QTextEdit, QSpinBox, QComboBox, QDateEdit {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #f5cba7;
                padding: 5px;
                border-radius: 4px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #f5cba7;
                selection-background-color: #e67e22;
                selection-color: #ffffff;
            }
            #searchBarAccueil { padding: 12px; font-size: 15px; border-radius: 6px; background-color: #ffffff; color: #000000; border: 1px solid #e67e22; }

            #rightPanel { border-left: 1px solid #f5cba7; }
            QPushButton { background-color: #fdebd0; color: #e67e22; border: 1px solid #e67e22; padding: 6px 12px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #e67e22; color: #ffffff; }
            QRadioButton { color: #000000; font-weight: bold; padding: 4px; }
        """
        self.setStyleSheet(theme_clair)
