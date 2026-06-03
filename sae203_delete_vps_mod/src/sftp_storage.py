from __future__ import annotations

import json
import posixpath
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path

import paramiko


class SftpStorageError(Exception):
    """Erreur liée au stockage SFTP."""


@dataclass
class SftpConfig:
    host: str
    port: int
    username: str
    password: str
    remote_base: str = "/commun"


def is_sftp_resource(resource: str | None) -> bool:
    """Indique si une ressource stockée en base correspond à un fichier SFTP."""
    return bool(resource and str(resource).startswith("sftp:"))


class SftpStorage:
    """
    Gestion simple du stockage distant SFTP.

    Le fichier de configuration attendu est :
    data/private/sftp_config.json
    """

    def __init__(self, config: SftpConfig):
        self.config = config

    @classmethod
    def from_project(cls, project_root: str | Path) -> "SftpStorage":
        project_root = Path(project_root)
        config_path = project_root / "data" / "private" / "sftp_config.json"

        if not config_path.exists():
            raise SftpStorageError(
                "Configuration SFTP introuvable. Crée le fichier : "
                f"{config_path}"
            )

        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SftpStorageError(
                f"Le fichier de configuration SFTP est invalide : {exc}"
            ) from exc

        required_keys = ["host", "username", "password"]
        missing = [key for key in required_keys if not data.get(key)]
        if missing:
            raise SftpStorageError(
                "Configuration SFTP incomplète. Clé(s) manquante(s) : "
                + ", ".join(missing)
            )

        return cls(
            SftpConfig(
                host=str(data["host"]),
                port=int(data.get("port", 22)),
                username=str(data["username"]),
                password=str(data["password"]),
                remote_base=str(data.get("remote_base", "/commun")),
            )
        )

    def _connect(self):
        """Ouvre une connexion SFTP et retourne transport + client SFTP."""
        try:
            transport = paramiko.Transport((self.config.host, self.config.port))
            transport.connect(
                username=self.config.username,
                password=self.config.password,
            )
            sftp = paramiko.SFTPClient.from_transport(transport)
            return transport, sftp
        except Exception as exc:
            raise SftpStorageError(f"Connexion SFTP impossible : {exc}") from exc

    def _ensure_remote_dir(self, sftp: paramiko.SFTPClient, remote_dir: str) -> None:
        """Crée le dossier distant s'il n'existe pas déjà."""
        parts = [part for part in remote_dir.split("/") if part]
        current = ""

        for part in parts:
            current = current + "/" + part
            try:
                sftp.stat(current)
            except FileNotFoundError:
                sftp.mkdir(current)

    def upload_file(self, source_file: str | Path) -> str:
        """
        Envoie un fichier local sur le serveur SFTP.

        Retourne une ressource stockable en base, par exemple :
        sftp:/commun/abc12345_document.pdf
        """
        source = Path(source_file)

        if not source.exists():
            raise SftpStorageError(f"Fichier source introuvable : {source}")

        safe_name = source.name.replace(" ", "_")
        remote_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
        remote_dir = self.config.remote_base.rstrip("/") or "/commun"
        remote_path = posixpath.join(remote_dir, remote_name)

        transport, sftp = self._connect()

        try:
            self._ensure_remote_dir(sftp, remote_dir)
            sftp.put(str(source), remote_path)
            return f"sftp:{remote_path}"
        except Exception as exc:
            raise SftpStorageError(f"Upload SFTP impossible : {exc}") from exc
        finally:
            sftp.close()
            transport.close()


    @staticmethod
    def metadata_path_for_resource(remote_resource: str) -> str:
        """
        Retourne le chemin du fichier JSON de métadonnées associé à une ressource.

        Exemple :
        sftp:/commun/abc_rapport.pdf -> /commun/abc_rapport.pdf.json
        """
        if not is_sftp_resource(remote_resource):
            raise SftpStorageError("La ressource demandée n'est pas une ressource SFTP.")
        remote_path = remote_resource.replace("sftp:", "", 1)
        return f"{remote_path}.json"

    def upload_metadata(self, metadata: dict, remote_resource: str) -> str:
        """
        Envoie les métadonnées JSON associées à un fichier partagé.

        Le fichier JSON est placé à côté du fichier réel sur le SFTP.
        Retourne une ressource de type : sftp:/commun/fichier.pdf.json
        """
        metadata_path = self.metadata_path_for_resource(remote_resource)
        remote_dir = posixpath.dirname(metadata_path)

        payload = dict(metadata)
        payload.setdefault("ressource", remote_resource)
        payload.setdefault("stockage", "partage")
        payload.setdefault("sync_version", 1)
        payload.setdefault("synced_at", datetime.now(timezone.utc).isoformat())

        data = json.dumps(payload, ensure_ascii=False, indent=2)

        transport, sftp = self._connect()
        try:
            self._ensure_remote_dir(sftp, remote_dir)
            with sftp.open(metadata_path, "w") as remote_file:
                remote_file.write(data)
            return f"sftp:{metadata_path}"
        except Exception as exc:
            raise SftpStorageError(f"Upload des métadonnées SFTP impossible : {exc}") from exc
        finally:
            sftp.close()
            transport.close()

    def list_metadata(self) -> list[dict]:
        """
        Lit tous les fichiers .json présents dans le dossier distant de partage.

        Chaque JSON représente un document partagé à synchroniser dans la base SQLite locale.
        """
        remote_dir = self.config.remote_base.rstrip("/") or "/commun"
        transport, sftp = self._connect()

        metadata_list: list[dict] = []
        try:
            try:
                filenames = sftp.listdir(remote_dir)
            except FileNotFoundError:
                return []

            for filename in filenames:
                if not filename.lower().endswith(".json"):
                    continue

                remote_path = posixpath.join(remote_dir, filename)
                try:
                    with sftp.open(remote_path, "r") as remote_file:
                        raw = remote_file.read()
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8")
                    data = json.loads(raw)
                    if isinstance(data, dict):
                        data.setdefault("metadata_resource", f"sftp:{remote_path}")
                        metadata_list.append(data)
                except Exception:
                    # Un JSON invalide ne doit pas bloquer toute la synchronisation.
                    continue

            return metadata_list
        except Exception as exc:
            raise SftpStorageError(f"Lecture des métadonnées SFTP impossible : {exc}") from exc
        finally:
            sftp.close()
            transport.close()

    def download_file(self, remote_resource: str, destination_file: str | Path) -> Path:
        """Télécharge un fichier SFTP vers un chemin local."""
        if not is_sftp_resource(remote_resource):
            raise SftpStorageError("La ressource demandée n'est pas une ressource SFTP.")

        remote_path = remote_resource.replace("sftp:", "", 1)
        destination = Path(destination_file)
        destination.parent.mkdir(parents=True, exist_ok=True)

        transport, sftp = self._connect()

        try:
            sftp.get(remote_path, str(destination))
            return destination
        except Exception as exc:
            raise SftpStorageError(f"Téléchargement SFTP impossible : {exc}") from exc
        finally:
            sftp.close()
            transport.close()

    @staticmethod
    def _is_missing_remote_file_error(exc: Exception) -> bool:
        """Détecte les erreurs SFTP correspondant à un fichier distant absent."""
        return (
            isinstance(exc, FileNotFoundError)
            or getattr(exc, "errno", None) == 2
            or "No such file" in str(exc)
            or "no such file" in str(exc)
        )

    def delete_file(self, remote_resource: str) -> None:
        """Supprime un fichier distant SFTP."""
        if not is_sftp_resource(remote_resource):
            raise SftpStorageError("La ressource demandée n'est pas une ressource SFTP.")

        remote_path = remote_resource.replace("sftp:", "", 1)
        transport, sftp = self._connect()

        try:
            sftp.remove(remote_path)
        except Exception as exc:
            if self._is_missing_remote_file_error(exc):
                return
            raise SftpStorageError(f"Suppression SFTP impossible : {exc}") from exc
        finally:
            sftp.close()
            transport.close()

    def delete_file_and_metadata(self, remote_resource: str) -> None:
        """
        Supprime un document partagé sur le SFTP.

        Cela supprime :
        - le fichier réel, par exemple /commun/abc_rapport.pdf ;
        - le fichier JSON de métadonnées, par exemple /commun/abc_rapport.pdf.json.

        Les fichiers déjà absents sont ignorés pour permettre de nettoyer
        la base locale même si le fichier a déjà été supprimé du VPS.
        """
        if not is_sftp_resource(remote_resource):
            raise SftpStorageError("La ressource demandée n'est pas une ressource SFTP.")

        remote_path = remote_resource.replace("sftp:", "", 1)
        metadata_path = self.metadata_path_for_resource(remote_resource)

        transport, sftp = self._connect()

        try:
            for path in (remote_path, metadata_path):
                try:
                    sftp.remove(path)
                except Exception as exc:
                    if self._is_missing_remote_file_error(exc):
                        continue
                    raise
        except Exception as exc:
            raise SftpStorageError(f"Suppression du fichier partagé sur le VPS impossible : {exc}") from exc
        finally:
            sftp.close()
            transport.close()
