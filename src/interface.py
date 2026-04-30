from __future__ import annotations

import os
import platform
import shutil
import subprocess
from datetime import date
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from src.logic import DocumentInput, LogicService, SearchFilters, ValidationError


class ZoneDetails(QFrame):
    """Panneau d'affichage du document sélectionné."""

    def __init__(self, project_root: str | Path):
        super().__init__()
        self.project_root = Path(project_root)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedWidth(320)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel('<b>Détails</b>'))
        self.label_titre = QLabel('Titre : ')
        self.label_auteur = QLabel('Auteur : ')
        self.label_date = QLabel('Date : ')
        self.label_categories = QLabel('Catégories : ')
        self.label_type = QLabel('Type : ')
        self.label_mots_cles = QLabel('Mots-clés : ')
        self.label_stockage = QLabel('Stockage : ')
        self.label_statut = QLabel('Statut : ')
        self.label_ressource = QLabel('Ressource : ')
        self.label_description = QLabel('Description : ')
        self.label_description.setWordWrap(True)

        for widget in (
            self.label_titre,
            self.label_auteur,
            self.label_date,
            self.label_categories,
            self.label_type,
            self.label_mots_cles,
            self.label_stockage,
            self.label_statut,
            self.label_ressource,
            self.label_description,
        ):
            layout.addWidget(widget)

        layout.addStretch()

        self.btn_ouvrir = QPushButton('📂 Ouvrir')
        self.btn_ouvrir.setEnabled(False)
        self.btn_ouvrir.clicked.connect(self.action_ouvrir)
        layout.addWidget(self.btn_ouvrir)

        self.chemin_actuel: str | None = None

    def clear(self) -> None:
        self.label_titre.setText('Titre : ')
        self.label_auteur.setText('Auteur : ')
        self.label_date.setText('Date : ')
        self.label_categories.setText('Catégories : ')
        self.label_type.setText('Type : ')
        self.label_mots_cles.setText('Mots-clés : ')
        self.label_stockage.setText('Stockage : ')
        self.label_statut.setText('Statut : ')
        self.label_ressource.setText('Ressource : ')
        self.label_description.setText('Description : ')
        self.chemin_actuel = None
        self.btn_ouvrir.setEnabled(False)

    def mettre_a_jour(self, document: dict) -> None:
        categories = ', '.join(document.get('categorie') or []) or '-'
        mots_cles = ', '.join(document.get('mots_cles') or []) or '-'
        ressource = document.get('ressource', '')
        chemin = self.project_root / ressource if ressource else None

        self.label_titre.setText(f"<b>Titre :</b> {document.get('titre', '')}")
        self.label_auteur.setText(f"<b>Auteur :</b> {document.get('auteur', '')}")
        self.label_date.setText(f"<b>Date :</b> {document.get('date', '')}")
        self.label_categories.setText(f"<b>Catégories :</b> {categories}")
        self.label_type.setText(f"<b>Type :</b> {document.get('type_fichier') or '-'}")
        self.label_mots_cles.setText(f"<b>Mots-clés :</b> {mots_cles}")
        self.label_stockage.setText(f"<b>Stockage :</b> {document.get('stockage') or '-'}")
        self.label_statut.setText(f"<b>Statut :</b> {document.get('statut') or '-'}")
        self.label_ressource.setText(f"<b>Ressource :</b> {ressource or '-'}")
        self.label_description.setText(f"<b>Description :</b> {document.get('description') or '-'}")

        if chemin and chemin.exists():
            self.chemin_actuel = str(chemin)
            self.btn_ouvrir.setEnabled(True)
        else:
            self.chemin_actuel = None
            self.btn_ouvrir.setEnabled(False)

    def action_ouvrir(self) -> None:
        if not self.chemin_actuel or not os.path.exists(self.chemin_actuel):
            QMessageBox.warning(self, 'Erreur', 'Le fichier sélectionné est introuvable.')
            return

        try:
            systeme = platform.system()
            if systeme == 'Windows':
                os.startfile(self.chemin_actuel)
            elif systeme == 'Darwin':
                subprocess.call(('open', self.chemin_actuel))
            else:
                subprocess.call(('xdg-open', self.chemin_actuel))
        except Exception as exc:
            QMessageBox.critical(self, 'Erreur', f"Échec de l'ouverture : {exc}")


class LogiqueSelectionFichier:
    """Sélection d'un fichier local."""

    def selectionner(self, parent_window: QWidget) -> str | None:
        fichier, _ = QFileDialog.getOpenFileName(
            parent_window,
            'Choisir un document à ajouter',
            '',
            'Documents (*.pdf *.doc *.docx *.xls *.xlsx);;Tous les fichiers (*)',
        )
        return fichier if fichier else None


class AddDocumentDialog(QDialog):
    """Formulaire simple d'ajout d'un document."""

    def __init__(self, project_root: str | Path, parent: QWidget | None = None):
        super().__init__(parent)
        self.project_root = Path(project_root)
        self.setWindowTitle('Ajouter un document')
        self.resize(480, 320)
        self.selected_file: str | None = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.edit_titre = QLineEdit()
        self.edit_auteur = QLineEdit()
        self.edit_auteur.setPlaceholderText('Ex: Fabien Amourani')
        self.edit_date = QLineEdit(date.today().isoformat())
        self.combo_stockage = QComboBox()
        self.combo_stockage.addItems(['local', 'partage'])
        self.edit_categories = QLineEdit()
        self.edit_categories.setPlaceholderText('Ex: Technique, Projet')
        self.edit_mots_cles = QLineEdit()
        self.edit_mots_cles.setPlaceholderText('Ex: sae203, urgent')
        self.edit_description = QTextEdit()
        self.edit_description.setFixedHeight(80)

        self.label_fichier = QLabel('Aucun fichier sélectionné')
        self.btn_parcourir = QPushButton('Sélectionner un fichier')
        self.btn_parcourir.clicked.connect(self.choisir_fichier)

        form.addRow('Titre', self.edit_titre)
        form.addRow('Auteur', self.edit_auteur)
        form.addRow('Date (YYYY-MM-DD)', self.edit_date)
        form.addRow('Stockage', self.combo_stockage)
        form.addRow('Catégories', self.edit_categories)
        form.addRow('Mots-clés', self.edit_mots_cles)
        form.addRow('Description', self.edit_description)
        form.addRow(self.btn_parcourir, self.label_fichier)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def choisir_fichier(self) -> None:
        path = LogiqueSelectionFichier().selectionner(self)
        if path:
            self.selected_file = path
            self.label_fichier.setText(os.path.basename(path))
            if not self.edit_titre.text().strip():
                self.edit_titre.setText(Path(path).stem.replace('_', ' ').strip())

    def build_payload(self) -> DocumentInput:
        if not self.selected_file:
            raise ValidationError('Veuillez sélectionner un fichier.')

        stockage = self.combo_stockage.currentText()
        relative_resource = self._copy_selected_file_to_storage(self.selected_file, stockage)
        suffix = Path(self.selected_file).suffix.upper().lstrip('.')

        return DocumentInput(
            titre=self.edit_titre.text(),
            auteur=self.edit_auteur.text(),
            date_document=self.edit_date.text(),
            ressource=relative_resource,
            description=self.edit_description.toPlainText(),
            categories=self.edit_categories.text(),
            mots_cles=self.edit_mots_cles.text(),
            stockage=stockage,
            chemin_fichier=relative_resource,
            type_fichier=suffix,
        )

    def _copy_selected_file_to_storage(self, source_file: str, stockage: str) -> str:
        source = Path(source_file)
        target_dir = self.project_root / 'documents' / stockage
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
        return str(target.relative_to(self.project_root)).replace('\\', '/')


class MainWindow(QMainWindow):
    def __init__(self, logic_service: LogicService, project_root: str | Path):
        super().__init__()
        self.logic = logic_service
        self.project_root = Path(project_root)
        self.setWindowTitle('SAE 203 - Gestion documentaire')
        self.resize(1100, 700)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)

        toolbar = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText('Rechercher par titre...')
        self.search_bar.returnPressed.connect(self.rechercher)
        self.btn_search = QPushButton('Rechercher')
        self.btn_search.clicked.connect(self.rechercher)
        self.btn_reset = QPushButton('Réinitialiser')
        self.btn_reset.clicked.connect(self.charger_documents)
        self.btn_add = QPushButton('Ajouter un document')
        self.btn_add.clicked.connect(self.ajouter_document)

        toolbar.addWidget(self.search_bar)
        toolbar.addWidget(self.btn_search)
        toolbar.addWidget(self.btn_reset)
        toolbar.addWidget(self.btn_add)
        left_layout.addLayout(toolbar)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(['Titre', 'Auteur', 'Date', 'Catégorie'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.afficher_detail_selection)
        left_layout.addWidget(self.table)

        main_layout.addWidget(left_container, stretch=4)

        self.details = ZoneDetails(self.project_root)
        main_layout.addWidget(self.details, stretch=2)

        self.changeColor()
        self.charger_documents()

    def changeColor(self) -> None:
        self.setStyleSheet(
            '''
            QMainWindow { background-color: white; }
            QLabel { color: black; }
            QLineEdit, QTextEdit, QComboBox { color: black; background-color: white; }
            QTableWidget { background-color: #f2f2f2; gridline-color: white; color: black; }
            QPushButton { color: black; background-color: #d7d7d7; padding: 6px 10px; }
            '''
        )

    def charger_documents(self) -> None:
        self.search_bar.clear()
        self._fill_table(self.logic.search_documents(SearchFilters()))

    def rechercher(self) -> None:
        try:
            terme = self.search_bar.text().strip()
            filters = SearchFilters(titre=terme)
            self._fill_table(self.logic.search_documents(filters))
        except ValidationError as exc:
            QMessageBox.warning(self, 'Validation', str(exc))
        except Exception as exc:
            QMessageBox.critical(self, 'Erreur', str(exc))

    def _fill_table(self, documents: list[dict]) -> None:
        self.table.setRowCount(0)
        self.details.clear()

        for row_index, doc in enumerate(documents):
            self.table.insertRow(row_index)
            categories = ', '.join(doc.get('categorie') or [])
            values = [doc.get('titre', ''), doc.get('auteur', ''), doc.get('date', ''), categories]

            for col_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole, doc.get('id'))
                self.table.setItem(row_index, col_index, item)

        if not documents:
            QMessageBox.information(self, 'Recherche', 'Aucun document trouvé.')

    def afficher_detail_selection(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        doc_id = self.table.item(items[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        if not doc_id:
            return
        try:
            document = self.logic.get_document_details(int(doc_id))
            self.details.mettre_a_jour(document)
        except Exception as exc:
            QMessageBox.critical(self, 'Erreur', str(exc))

    def ajouter_document(self) -> None:
        dialog = AddDocumentDialog(self.project_root, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            payload = dialog.build_payload()
            doc_id = self.logic.add_document(payload)
            QMessageBox.information(self, 'Ajout', f'Document ajouté avec succès (id {doc_id}).')
            self._fill_table(self.logic.search_documents(SearchFilters()))
        except ValidationError as exc:
            QMessageBox.warning(self, 'Validation', str(exc))
        except Exception as exc:
            QMessageBox.critical(self, 'Erreur', str(exc))
