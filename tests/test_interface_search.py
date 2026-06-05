import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.database import SQLiteRepository
from src.interface import MainWindow
from src.logic import LogicService


class InterfaceSearchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        repository = SQLiteRepository(
            Path(self.temp_dir.name) / "documents.db",
            PROJECT_ROOT / "data" / "schema_documents_sqlite.sql",
            PROJECT_ROOT,
        )
        self.window = MainWindow(LogicService(repository), PROJECT_ROOT)

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.temp_dir.cleanup()

    def table_titles(self):
        return [
            self.window.table.item(row, 0).text()
            for row in range(self.window.table.rowCount())
        ]

    def table_authors(self):
        return [
            self.window.table.item(row, 1).text()
            for row in range(self.window.table.rowCount())
        ]

    def table_dates(self):
        return [
            self.window.table.item(row, 2).text()
            for row in range(self.window.table.rowCount())
        ]

    def table_storages(self):
        return [
            self.window.table.item(row, 0).data(Qt.ItemDataRole.UserRole)["stockage"]
            for row in range(self.window.table.rowCount())
        ]

    def check_category(self, category):
        model = self.window.search_categories._items_model
        for row in range(model.rowCount()):
            item = model.item(row)
            if item.text() == category:
                item.setCheckState(Qt.CheckState.Checked)
                self.window.search_categories._update_display_text()
                return
        self.fail(f"Catégorie introuvable dans l'interface : {category}")

    def test_chargement_initial(self):
        self.assertEqual(self.window.table.rowCount(), 0)
        self.assertEqual(self.window.search_bar_accueil.width(), 470)
        self.assertEqual(self.window.btn_accueil_rechercher.width(), 105)
        self.assertEqual(self.window.btn_accueil_recherche_avancee.width(), 145)
        self.assertEqual(self.window.search_bar_accueil.height(), 44)
        self.assertEqual(self.window.btn_accueil_rechercher.height(), 44)
        self.assertEqual(self.window.btn_accueil_recherche_avancee.height(), 44)
        self.assertTrue(self.window.accueil_advanced_container.isHidden())
        self.assertEqual(self.window.btn_accueil_recherche_avancee.text(), "Recherche avancée")
        self.assertTrue(self.window.search_advanced_container.isHidden())
        self.assertEqual(self.window.btn_recherche_avancee.text(), "Recherche avancée")

    def test_bouton_rechercher_accueil_lance_la_recherche(self):
        self.window.search_bar_accueil.setText("contrat")

        self.window.btn_accueil_rechercher.click()

        self.assertTrue(self.window.accueil_container.isHidden())
        self.assertEqual(self.window.search_titre.text(), "contrat")
        self.assertEqual(self.window.table.rowCount(), 1)

    def test_recherche_avancee_accueil_affiche_et_masque_les_filtres(self):
        self.window.btn_accueil_recherche_avancee.click()

        self.assertFalse(self.window.accueil_advanced_container.isHidden())
        self.assertEqual(
            self.window.btn_accueil_recherche_avancee.text(),
            "Masquer la recherche avancée",
        )

        self.window.btn_accueil_recherche_avancee.click()

        self.assertTrue(self.window.accueil_advanced_container.isHidden())
        self.assertEqual(self.window.btn_accueil_recherche_avancee.text(), "Recherche avancée")

    def test_recherche_avancee_depuis_accueil(self):
        self.window.btn_accueil_recherche_avancee.click()
        self.window.search_bar_accueil.setText("liste")
        self.window.accueil_stockage.setCurrentIndex(1)
        self.window.accueil_sort_by.setCurrentIndex(1)
        self.window.accueil_sort_order.setCurrentIndex(1)

        self.window.executer_recherche_accueil()

        self.assertTrue(self.window.accueil_container.isHidden())
        self.assertFalse(self.window.left_container.isHidden())
        self.assertEqual(self.window.search_titre.text(), "liste")
        self.assertEqual(self.window.search_stockage.currentData(), "local")
        self.assertEqual(self.window.search_sort_by.currentData(), "titre")
        self.assertEqual(self.window.search_sort_order.currentData(), "asc")
        self.assertGreater(self.window.table.rowCount(), 0)
        self.assertEqual(set(self.table_storages()), {"local"})

    def test_recherche_avancee_principale_affiche_et_masque_les_filtres(self):
        self.window.btn_recherche_avancee.click()

        self.assertFalse(self.window.search_advanced_container.isHidden())
        self.assertEqual(
            self.window.btn_recherche_avancee.text(),
            "Masquer la recherche avancée",
        )

        self.window.btn_recherche_avancee.click()

        self.assertTrue(self.window.search_advanced_container.isHidden())
        self.assertEqual(self.window.btn_recherche_avancee.text(), "Recherche avancée")

    def test_recherche_sans_filtre_affiche_tous_les_documents(self):
        self.window.rechercherDocuments()

        self.assertEqual(self.window.table.rowCount(), 12)
        self.assertEqual(self.window.table.item(0, 2).text(), "2026-04-18")
        self.assertIn("local", self.table_storages())
        self.assertIn("partage", self.table_storages())

    def test_recherche_simple_par_titre(self):
        self.window.search_titre.setText("contrat")
        self.window.rechercherDocuments()

        self.assertEqual(self.window.table.rowCount(), 1)
        self.assertEqual(self.table_titles(), ["Contrat de stage - exemple"])

    def test_combinaison_de_filtres(self):
        self.window.search_auteur.setText("Fabien")
        self.check_category("Rapport")
        self.window.rechercherDocuments()

        self.assertEqual(self.window.table.rowCount(), 1)
        self.assertEqual(self.table_titles(), ["Rapport activite reseau"])

    def test_reinitialisation(self):
        self.window.btn_recherche_avancee.click()
        self.window.search_titre.setText("contrat")
        self.window.rechercherDocuments()
        self.assertEqual(self.window.table.rowCount(), 1)

        self.window.reinitialiserRecherche()

        self.assertFalse(self.window.search_advanced_container.isHidden())
        self.assertEqual(self.window.table.rowCount(), 0)
        self.assertEqual(self.window.search_titre.text(), "")
        self.assertEqual(self.window.search_auteur.text(), "")
        self.assertEqual(self.window.search_mots_cles.text(), "")
        self.assertEqual(self.window.search_categories.checked_items(), [])
        self.assertEqual(self.window.search_stockage.currentData(), "tous")
        self.assertEqual(self.window.search_sort_by.currentData(), "date")
        self.assertEqual(self.window.search_sort_order.currentData(), "desc")

    def test_filtre_stockage_local(self):
        self.window.btn_recherche_avancee.click()
        self.window.search_stockage.setCurrentIndex(1)
        self.window.rechercherDocuments()

        self.assertFalse(self.window.search_advanced_container.isHidden())
        self.assertGreater(self.window.table.rowCount(), 0)
        self.assertEqual(set(self.table_storages()), {"local"})

    def test_filtre_stockage_partage(self):
        self.window.btn_recherche_avancee.click()
        self.window.search_stockage.setCurrentIndex(2)
        self.window.rechercherDocuments()

        self.assertFalse(self.window.search_advanced_container.isHidden())
        self.assertGreater(self.window.table.rowCount(), 0)
        self.assertEqual(set(self.table_storages()), {"partage"})

    def test_tri_par_date_decroissante_par_defaut(self):
        self.window.rechercherDocuments()

        self.assertEqual(self.window.search_sort_by.currentData(), "date")
        self.assertEqual(self.window.search_sort_order.currentData(), "desc")
        self.assertEqual(self.table_dates()[0], "2026-04-18")
        self.assertEqual(self.table_dates()[-1], "2026-04-01")

    def test_tri_par_date_croissante(self):
        self.window.search_sort_order.setCurrentIndex(1)
        self.window.rechercherDocuments()

        self.assertEqual(self.table_dates()[0], "2026-04-01")
        self.assertEqual(self.table_dates()[-1], "2026-04-18")

    def test_tri_par_titre_croissant_et_decroissant(self):
        self.window.search_sort_by.setCurrentIndex(1)
        self.window.search_sort_order.setCurrentIndex(1)
        self.window.rechercherDocuments()
        self.assertEqual(self.table_titles()[0], "Bilan mensuel avril")

        self.window.search_sort_order.setCurrentIndex(0)
        self.window.rechercherDocuments()
        self.assertEqual(self.table_titles()[0], "Rapport activite reseau")

    def test_tri_par_auteur_croissant_et_decroissant(self):
        self.window.search_sort_by.setCurrentIndex(2)
        self.window.search_sort_order.setCurrentIndex(1)
        self.window.rechercherDocuments()
        self.assertEqual(self.table_authors()[0], "Fabien AMOURANI")

        self.window.search_sort_order.setCurrentIndex(0)
        self.window.rechercherDocuments()
        self.assertEqual(self.table_authors()[0], "Lucas MOUNIAMA")

    def test_tri_apres_recherche_simple(self):
        self.window.search_titre.setText("de")
        self.window.search_sort_by.setCurrentIndex(1)
        self.window.search_sort_order.setCurrentIndex(1)
        self.window.rechercherDocuments()

        self.assertEqual(self.window.table.rowCount(), 4)
        self.assertEqual(self.table_titles()[0], "Contrat de stage - exemple")
        self.assertEqual(self.window.search_titre.text(), "de")

    def test_tri_apres_recherche_multicritere(self):
        self.window.search_auteur.setText("Manon")
        self.check_category("Projet")
        self.window.search_sort_by.setCurrentIndex(1)
        self.window.search_sort_order.setCurrentIndex(0)
        self.window.rechercherDocuments()

        self.assertEqual(self.window.table.rowCount(), 2)
        self.assertEqual(
            self.table_titles(),
            ["Planning de deploiement", "Bilan mensuel avril"],
        )
        self.assertEqual(self.window.search_auteur.text(), "Manon")
        self.assertEqual(self.window.search_categories.checked_items(), ["Projet"])


if __name__ == "__main__":
    unittest.main()
