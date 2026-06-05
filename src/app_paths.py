from __future__ import annotations

import shutil
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    """Chemins principaux de l'application."""

    project_root: Path
    bundled_root: Path


def _development_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_app_paths() -> AppPaths:
    """
    Retourne la racine modifiable et la racine des fichiers embarqués.

    En développement, les deux racines sont le dossier du projet.
    En exécutable, project_root est le dossier à côté de l'exécutable.
    """
    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        bundled_root = Path(getattr(sys, "_MEIPASS", executable_dir / "_internal"))
        return AppPaths(project_root=executable_dir, bundled_root=bundled_root)

    root = _development_root()
    return AppPaths(project_root=root, bundled_root=root)


def _copy_file_if_missing(source: Path, destination: Path) -> None:
    if not source.exists() or destination.exists():
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _copy_tree_files_if_missing(source_dir: Path, destination_dir: Path) -> None:
    if not source_dir.exists():
        return

    for source in source_dir.rglob("*"):
        if source.is_dir():
            continue

        destination = destination_dir / source.relative_to(source_dir)
        _copy_file_if_missing(source, destination)


def bootstrap_external_data(project_root: str | Path, bundled_root: str | Path) -> None:
    """
    Prépare le dossier data modifiable utilisé par l'exécutable.

    Les fichiers présents dans le bundle PyInstaller servent seulement de base
    initiale. Les fichiers déjà créés ou modifiés par l'utilisateur sont gardés.
    """
    project_root = Path(project_root)
    bundled_root = Path(bundled_root)

    data_dir = project_root / "data"
    for directory in [
        data_dir / "documents" / "local",
        data_dir / "documents" / "partage",
        data_dir / "documents" / "cache",
        data_dir / "metadata" / "documents",
        data_dir / "private",
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    bundled_data = bundled_root / "data"
    _copy_file_if_missing(
        bundled_data / "schema_documents_sqlite.sql",
        data_dir / "schema_documents_sqlite.sql",
    )
    _copy_tree_files_if_missing(
        bundled_data / "metadata" / "documents",
        data_dir / "metadata" / "documents",
    )
    _copy_tree_files_if_missing(
        bundled_data / "documents" / "local",
        data_dir / "documents" / "local",
    )
    _copy_tree_files_if_missing(
        bundled_data / "documents" / "partage",
        data_dir / "documents" / "partage",
    )
    _copy_file_if_missing(
        bundled_data / "private" / "sftp_config.json",
        data_dir / "private" / "sftp_config.json",
    )


def write_startup_error_log(project_root: str | Path, exc: BaseException) -> Path:
    """Écrit une erreur de démarrage dans un fichier visible à côté de l'exécutable."""
    project_root = Path(project_root)
    project_root.mkdir(parents=True, exist_ok=True)
    log_path = project_root / "sowedrop_error.log"
    content = [
        f"Erreur de demarrage SoweDrop - {datetime.now().isoformat(timespec='seconds')}",
        "",
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    ]
    log_path.write_text("\n".join(content), encoding="utf-8")
    return log_path
