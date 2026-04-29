import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from src.logic import LogicService, DocumentInput, SearchFilters, ValidationError


class FakeRepository:
    def __init__(self):
        self.documents = []
        self.histories = []
        self.categories_links = {}
        self.keywords_links = {}

    def insert_document(self, document_data):
        new_id = len(self.documents) + 1
        document_data = dict(document_data)
        document_data["id"] = new_id
        self.documents.append(document_data)
        return new_id

    def link_categories_to_document(self, document_id, categories):
        self.categories_links[document_id] = categories

    def link_keywords_to_document(self, document_id, keywords):
        self.keywords_links[document_id] = keywords

    def add_history(self, document_id, objet):
        self.histories.append({"document_id": document_id, "objet": objet})

    def search_documents(self, prepared_filters):
        results = list(self.documents)

        if prepared_filters["titre_like"]:
            results = [
                d for d in results
                if prepared_filters["titre_like"].lower() in d["titre"].lower()
            ]

        if prepared_filters["auteur_like"]:
            results = [
                d for d in results
                if prepared_filters["auteur_like"].lower() in d["auteur"].lower()
            ]

        if prepared_filters["ressource_like"]:
            results = [
                d for d in results
                if prepared_filters["ressource_like"].lower() in d["ressource"].lower()
            ]

        if prepared_filters["date_min"]:
            results = [
                d for d in results
                if d["date_document"] >= prepared_filters["date_min"]
            ]

        if prepared_filters["date_max"]:
            results = [
                d for d in results
                if d["date_document"] <= prepared_filters["date_max"]
            ]

        return results

    def get_document_by_id(self, document_id):
        for doc in self.documents:
            if doc["id"] == document_id:
                return doc
        return None

    def archive_document(self, document_id):
        for doc in self.documents:
            if doc["id"] == document_id:
                doc["archived"] = True

    def delete_document(self, document_id):
        self.documents = [d for d in self.documents if d["id"] != document_id]

    def document_belongs_to_user(self, document_id, user_id):
        for doc in self.documents:
            if doc["id"] == document_id and doc.get("user_id") == user_id:
                return True
        return False


def test_add_document_ok():
    repo = FakeRepository()
    logic = LogicService(repo)

    payload = DocumentInput(
        titre="Contrat RH",
        auteur="Fabien",
        date_document="2026-04-20",
        ressource="PDF",
        description="Contrat important",
        categories=["RH"],
        mots_cles=["contrat", "urgent"],
        user_id=1,
        stockage="local"
    )

    doc_id = logic.add_document(payload)

    assert doc_id == 1
    assert len(repo.documents) == 1
    assert repo.documents[0]["titre"] == "Contrat RH"
    assert repo.documents[0]["auteur"] == "Fabien"
    assert repo.documents[0]["date_document"] == "2026-04-20"
    assert repo.documents[0]["ressource"] == "PDF"
    assert repo.categories_links[1] == ["RH"]
    assert repo.keywords_links[1] == ["contrat", "urgent"]
    assert repo.histories[0]["objet"] == "Création du document"


def test_add_document_without_title():
    repo = FakeRepository()
    logic = LogicService(repo)

    payload = DocumentInput(
        titre="",
        auteur="Fabien",
        date_document="2026-04-20",
        ressource="PDF"
    )

    with pytest.raises(ValidationError):
        logic.add_document(payload)


def test_add_document_without_author():
    repo = FakeRepository()
    logic = LogicService(repo)

    payload = DocumentInput(
        titre="Facture",
        auteur="",
        date_document="2026-04-20",
        ressource="PDF"
    )

    with pytest.raises(ValidationError):
        logic.add_document(payload)


def test_add_document_invalid_date():
    repo = FakeRepository()
    logic = LogicService(repo)

    payload = DocumentInput(
        titre="Facture",
        auteur="Fabien",
        date_document="20/04/2026",
        ressource="PDF"
    )

    with pytest.raises(ValidationError):
        logic.add_document(payload)


def test_search_by_title():
    repo = FakeRepository()
    logic = LogicService(repo)

    logic.add_document(DocumentInput(
        titre="Contrat RH",
        auteur="Fabien",
        date_document="2026-04-20",
        ressource="PDF"
    ))

    logic.add_document(DocumentInput(
        titre="Facture Internet",
        auteur="Alice",
        date_document="2026-04-21",
        ressource="PDF"
    ))

    filters = SearchFilters(titre="contrat")
    results = logic.search_documents(filters)

    assert len(results) == 1
    assert results[0]["titre"] == "Contrat RH"


def test_search_by_author():
    repo = FakeRepository()
    logic = LogicService(repo)

    logic.add_document(DocumentInput(
        titre="Rapport",
        auteur="Fabien",
        date_document="2026-04-20",
        ressource="PDF"
    ))

    logic.add_document(DocumentInput(
        titre="Facture",
        auteur="Alice",
        date_document="2026-04-21",
        ressource="PDF"
    ))

    filters = SearchFilters(auteur="Fabien")
    results = logic.search_documents(filters)

    assert len(results) == 1
    assert results[0]["auteur"] == "Fabien"


def test_search_without_filters_returns_all():
    repo = FakeRepository()
    logic = LogicService(repo)

    logic.add_document(DocumentInput(
        titre="Doc 1",
        auteur="Fabien",
        date_document="2026-04-20",
        ressource="PDF"
    ))

    logic.add_document(DocumentInput(
        titre="Doc 2",
        auteur="Alice",
        date_document="2026-04-21",
        ressource="PDF"
    ))

    filters = SearchFilters()
    results = logic.search_documents(filters)

    assert len(results) == 2


def test_search_invalid_date_range():
    repo = FakeRepository()
    logic = LogicService(repo)

    filters = SearchFilters(
        date_min="2026-05-01",
        date_max="2026-04-01"
    )

    with pytest.raises(ValidationError):
        logic.search_documents(filters)