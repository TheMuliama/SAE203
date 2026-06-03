import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import SQLiteRepository
from src.logic import LogicService, SearchFilters, ValidationError


class LogicStorageFilterTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repository = SQLiteRepository(
            Path(self.temp_dir.name) / "documents.db",
            PROJECT_ROOT / "data" / "schema_documents_sqlite.sql",
            PROJECT_ROOT,
        )
        self.logic = LogicService(self.repository)

    def tearDown(self):
        self.temp_dir.cleanup()

    def storages(self, filters):
        return [document["stockage"] for document in self.logic.search_documents(filters)]

    def test_filtre_tous_retourne_local_et_partage(self):
        storages = self.storages(SearchFilters())

        self.assertIn("local", storages)
        self.assertIn("partage", storages)

    def test_filtre_local(self):
        storages = self.storages(SearchFilters(stockage="local"))

        self.assertGreater(len(storages), 0)
        self.assertEqual(Counter(storages), {"local": len(storages)})

    def test_filtre_partage(self):
        storages = self.storages(SearchFilters(stockage="partage"))

        self.assertGreater(len(storages), 0)
        self.assertEqual(Counter(storages), {"partage": len(storages)})

    def test_filtre_stockage_invalide_refuse(self):
        with self.assertRaises(ValidationError):
            self.logic.search_documents(SearchFilters(stockage="distant"))


if __name__ == "__main__":
    unittest.main()
