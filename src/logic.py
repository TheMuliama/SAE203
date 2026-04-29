from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Protocol, Any


# ============================================================
# Exceptions métier
# ============================================================

class LogicError(Exception):
    """Erreur métier générale."""
    pass


class ValidationError(LogicError):
    """Erreur de validation des données."""
    pass


class NotFoundError(LogicError):
    """Objet introuvable."""
    pass


class PermissionError(LogicError):
    """Erreur d'autorisation métier."""
    pass


# ============================================================
# Structures de données
# ============================================================

@dataclass
class DocumentInput:
    titre: str
    auteur: str
    date_document: str | date
    ressource: str
    description: str = ""
    categories: list[str] = field(default_factory=list)
    mots_cles: list[str] = field(default_factory=list)
    user_id: int | None = None
    stockage: str = "local"   # local | shared
    chemin_fichier: str | None = None


@dataclass
class SearchFilters:
    titre: str = ""
    auteur: str = ""
    categories: list[str] = field(default_factory=list)
    mots_cles: list[str] = field(default_factory=list)
    date_min: str | date | None = None
    date_max: str | date | None = None
    ressource: str = ""
    sort_by: str = "date"     # date | titre | auteur
    sort_order: str = "desc"  # desc | asc


# ============================================================
# Contrat attendu côté database.py
# ============================================================

class DatabaseRepository(Protocol):
    def insert_document(self, document_data: dict[str, Any]) -> int:
        ...

    def link_categories_to_document(self, document_id: int, categories: list[str]) -> None:
        ...

    def link_keywords_to_document(self, document_id: int, keywords: list[str]) -> None:
        ...

    def add_history(self, document_id: int, objet: str) -> None:
        ...

    def search_documents(self, prepared_filters: dict[str, Any]) -> list[dict[str, Any]]:
        ...

    def get_document_by_id(self, document_id: int) -> dict[str, Any] | None:
        ...

    def archive_document(self, document_id: int) -> None:
        ...

    def delete_document(self, document_id: int) -> None:
        ...

    def document_belongs_to_user(self, document_id: int, user_id: int) -> bool:
        ...


# ============================================================
# Logique métier
# ============================================================

class LogicService:
    """
    Service métier principal.

    Rôle :
    - vérifier les données
    - préparer les filtres de recherche
    - appeler database.py
    """

    ALLOWED_SORT_FIELDS = {"date": "date_document", "titre": "titre", "auteur": "auteur"}
    ALLOWED_SORT_ORDER = {"asc", "desc"}
    ALLOWED_STORAGE = {"local", "shared"}

    def __init__(self, repository: DatabaseRepository):
        self.repository = repository

    # --------------------------------------------------------
    # Ajout document
    # --------------------------------------------------------
    def add_document(self, payload: DocumentInput) -> int:
        """
        Ajoute un document après validation métier.
        Retourne l'id du document créé.
        """
        normalized = self._validate_and_normalize_document(payload)

        document_id = self.repository.insert_document({
            "titre": normalized.titre,
            "auteur": normalized.auteur,
            "date_document": self._date_to_iso(normalized.date_document),
            "ressource": normalized.ressource,
            "description": normalized.description,
            "user_id": normalized.user_id,
            "stockage": normalized.stockage,
            "chemin_fichier": normalized.chemin_fichier,
        })

        if normalized.categories:
            self.repository.link_categories_to_document(document_id, normalized.categories)

        if normalized.mots_cles:
            self.repository.link_keywords_to_document(document_id, normalized.mots_cles)

        self.repository.add_history(document_id, "Création du document")

        return document_id

    # --------------------------------------------------------
    # Recherche multicritère
    # --------------------------------------------------------
    def search_documents(self, filters: SearchFilters) -> list[dict[str, Any]]:
        """
        Prépare les filtres métier selon la spécification du document,
        puis délègue la requête SQL à database.py.
        """
        prepared_filters = self._prepare_search_filters(filters)
        results = self.repository.search_documents(prepared_filters)

        return [self._format_document_result(doc) for doc in results]

    # --------------------------------------------------------
    # Consultation
    # --------------------------------------------------------
    def get_document_details(self, document_id: int) -> dict[str, Any]:
        if not isinstance(document_id, int) or document_id <= 0:
            raise ValidationError("Identifiant de document invalide.")

        document = self.repository.get_document_by_id(document_id)
        if document is None:
            raise NotFoundError("Document introuvable.")

        return self._format_document_result(document)

    # --------------------------------------------------------
    # Archivage / suppression
    # --------------------------------------------------------
    def archive_document(self, document_id: int, user_id: int) -> None:
        self._check_document_permission(document_id, user_id)
        self.repository.archive_document(document_id)
        self.repository.add_history(document_id, "Archivage du document")

    def delete_document(self, document_id: int, user_id: int) -> None:
        self._check_document_permission(document_id, user_id)
        self.repository.delete_document(document_id)

    # ========================================================
    # Validation document
    # ========================================================
    def _validate_and_normalize_document(self, payload: DocumentInput) -> DocumentInput:
        titre = self._clean_text(payload.titre)
        auteur = self._clean_text(payload.auteur)
        ressource = self._clean_text(payload.ressource)
        description = self._clean_text(payload.description, allow_empty=True)
        stockage = self._clean_text(payload.stockage).lower()

        if not titre:
            raise ValidationError("Le titre est obligatoire.")

        if not auteur:
            raise ValidationError("L'auteur est obligatoire.")

        if not ressource:
            raise ValidationError("La ressource est obligatoire.")

        if stockage not in self.ALLOWED_STORAGE:
            raise ValidationError("Le mode de stockage doit être 'local' ou 'shared'.")

        parsed_date = self._parse_date(payload.date_document)
        if parsed_date is None:
            raise ValidationError("La date du document est obligatoire et doit être valide (YYYY-MM-DD).")

        categories = self._normalize_string_list(payload.categories)
        mots_cles = self._normalize_string_list(payload.mots_cles)

        return DocumentInput(
            titre=titre,
            auteur=auteur,
            date_document=parsed_date,
            ressource=ressource,
            description=description,
            categories=categories,
            mots_cles=mots_cles,
            user_id=payload.user_id,
            stockage=stockage,
            chemin_fichier=payload.chemin_fichier,
        )

    # ========================================================
    # Préparation filtres recherche
    # ========================================================
    def _prepare_search_filters(self, filters: SearchFilters) -> dict[str, Any]:
        titre = self._clean_text(filters.titre, allow_empty=True)
        auteur = self._clean_text(filters.auteur, allow_empty=True)
        ressource = self._clean_text(filters.ressource, allow_empty=True)

        categories = self._normalize_string_list(filters.categories)
        mots_cles = self._normalize_string_list(filters.mots_cles)

        date_min = self._parse_date(filters.date_min) if filters.date_min else None
        date_max = self._parse_date(filters.date_max) if filters.date_max else None

        if date_min and date_max and date_min > date_max:
            raise ValidationError("La date minimale ne peut pas être supérieure à la date maximale.")

        sort_by = filters.sort_by.lower().strip() if filters.sort_by else "date"
        if sort_by not in self.ALLOWED_SORT_FIELDS:
            sort_by = "date"

        sort_order = filters.sort_order.lower().strip() if filters.sort_order else "desc"
        if sort_order not in self.ALLOWED_SORT_ORDER:
            sort_order = "desc"

        return {
            "titre_like": titre or None,
            "auteur_like": auteur or None,
            "ressource_like": ressource or None,
            "categories_exact_or": categories or [],
            "mots_cles_like_or": mots_cles or [],
            "date_min": self._date_to_iso(date_min) if date_min else None,
            "date_max": self._date_to_iso(date_max) if date_max else None,
            "sort_column": self.ALLOWED_SORT_FIELDS[sort_by],
            "sort_order": sort_order,
        }

    # ========================================================
    # Formatage / permissions
    # ========================================================
    def _format_document_result(self, doc: dict[str, Any]) -> dict[str, Any]:
        """
        Normalise le résultat pour l'interface.
        """
        return {
            "id": doc.get("id") or doc.get("idDoc"),
            "titre": doc.get("titre", ""),
            "auteur": doc.get("auteur", ""),
            "description": doc.get("description", ""),
            "date": doc.get("date_document") or doc.get("date", ""),
            "categorie": doc.get("categorie") or doc.get("categories") or [],
            "ressource": doc.get("ressource", ""),
            "mots_cles": doc.get("mots_cles") or [],
            "chemin_fichier": doc.get("chemin_fichier"),
            "stockage": doc.get("stockage"),
        }

    def _check_document_permission(self, document_id: int, user_id: int) -> None:
        if not isinstance(document_id, int) or document_id <= 0:
            raise ValidationError("Identifiant de document invalide.")

        if not isinstance(user_id, int) or user_id <= 0:
            raise ValidationError("Identifiant utilisateur invalide.")

        belongs = self.repository.document_belongs_to_user(document_id, user_id)
        if not belongs:
            raise PermissionError("Vous ne pouvez pas modifier ou supprimer un document qui ne vous appartient pas.")

    # ========================================================
    # Helpers
    # ========================================================
    @staticmethod
    def _clean_text(value: Any, allow_empty: bool = False) -> str:
        if value is None:
            return "" if allow_empty else ""

        text = str(value).strip()
        if not text and not allow_empty:
            return ""
        return text

    @staticmethod
    def _normalize_string_list(values: list[str] | str | None) -> list[str]:
        """
        Accepte :
        - ["urgent", "pdf"]
        - "urgent, pdf"
        - None
        """
        if values is None:
            return []

        if isinstance(values, str):
            raw_items = values.split(",")
        else:
            raw_items = values

        cleaned = []
        seen = set()

        for item in raw_items:
            text = str(item).strip()
            if not text:
                continue

            lowered = text.lower()
            if lowered not in seen:
                seen.add(lowered)
                cleaned.append(text)

        return cleaned

    @staticmethod
    def _parse_date(value: str | date | None) -> date | None:
        if value is None:
            return None

        if isinstance(value, date):
            return value

        text = str(value).strip()
        if not text:
            return None

        try:
            return datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def _date_to_iso(value: date | None) -> str | None:
        return value.isoformat() if value else None