import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app_paths import bootstrap_external_data, get_app_paths


class ExecutablePathsTest(unittest.TestCase):
    def test_developpement_utilise_la_racine_du_projet(self):
        with patch.object(sys, "frozen", False, create=True):
            paths = get_app_paths()

        self.assertEqual(paths.project_root, PROJECT_ROOT)
        self.assertEqual(paths.bundled_root, PROJECT_ROOT)

    def test_executable_utilise_le_dossier_de_lexecutable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            executable_dir = Path(temp_dir) / "SoweDrop"
            bundled_dir = executable_dir / "_internal"
            executable_dir.mkdir()
            bundled_dir.mkdir()

            with (
                patch.object(sys, "frozen", True, create=True),
                patch.object(sys, "executable", str(executable_dir / "SoweDrop"), create=True),
                patch.object(sys, "_MEIPASS", str(bundled_dir), create=True),
            ):
                paths = get_app_paths()

            self.assertEqual(paths.project_root, executable_dir)
            self.assertEqual(paths.bundled_root, bundled_dir)

    def test_bootstrap_copie_les_donnees_initiales_sans_ecraser(self):
        with tempfile.TemporaryDirectory() as external_temp, tempfile.TemporaryDirectory() as bundle_temp:
            project_root = Path(external_temp)
            bundled_root = Path(bundle_temp)

            (bundled_root / "data" / "metadata" / "documents").mkdir(parents=True)
            (bundled_root / "data" / "documents" / "local").mkdir(parents=True)
            (bundled_root / "data" / "private").mkdir(parents=True)

            (bundled_root / "data" / "schema_documents_sqlite.sql").write_text(
                "-- schema initial",
                encoding="utf-8",
            )
            (bundled_root / "data" / "metadata" / "documents" / "01_test.txt").write_text(
                "titre: Test",
                encoding="utf-8",
            )
            (bundled_root / "data" / "documents" / "local" / "test.pdf").write_bytes(b"pdf")
            (bundled_root / "data" / "private" / "sftp_config.json").write_text(
                '{"host": "initial"}',
                encoding="utf-8",
            )
            (bundled_root / "data" / "documents.db").write_bytes(b"base embarquee")

            bootstrap_external_data(project_root, bundled_root)

            self.assertTrue((project_root / "data" / "documents" / "cache").is_dir())
            self.assertTrue((project_root / "data" / "documents" / "partage").is_dir())
            self.assertEqual(
                (project_root / "data" / "schema_documents_sqlite.sql").read_text(encoding="utf-8"),
                "-- schema initial",
            )
            self.assertTrue((project_root / "data" / "metadata" / "documents" / "01_test.txt").exists())
            self.assertTrue((project_root / "data" / "documents" / "local" / "test.pdf").exists())
            self.assertEqual(
                (project_root / "data" / "private" / "sftp_config.json").read_text(encoding="utf-8"),
                '{"host": "initial"}',
            )
            self.assertFalse((project_root / "data" / "documents.db").exists())

            (project_root / "data" / "private" / "sftp_config.json").write_text(
                '{"host": "personnalise"}',
                encoding="utf-8",
            )
            (bundled_root / "data" / "private" / "sftp_config.json").write_text(
                '{"host": "nouveau"}',
                encoding="utf-8",
            )

            bootstrap_external_data(project_root, bundled_root)

            self.assertEqual(
                (project_root / "data" / "private" / "sftp_config.json").read_text(encoding="utf-8"),
                '{"host": "personnalise"}',
            )


if __name__ == "__main__":
    unittest.main()
