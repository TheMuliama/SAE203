import sys

from PyQt6.QtWidgets import QApplication

from src.app_paths import bootstrap_external_data, get_app_paths, write_startup_error_log
from src.database import build_repository
from src.interface import MainWindow
from src.logic import LogicService


def main():
    paths = get_app_paths()

    try:
        # Prépare les dossiers modifiables avant d'ouvrir la base SQLite.
        bootstrap_external_data(paths.project_root, paths.bundled_root)

        # Prépare l'application, les services, la fenêtre principale, puis lance la boucle Qt.
        app = QApplication(sys.argv)

        repository = build_repository(paths.project_root)
        logic_service = LogicService(repository)

        window = MainWindow(logic_service, paths.project_root)
        window.show()
        sys.exit(app.exec())
    except Exception as exc:
        write_startup_error_log(paths.project_root, exc)
        raise


if __name__ == "__main__":
    main()
