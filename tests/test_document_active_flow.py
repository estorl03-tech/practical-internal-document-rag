from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app import main
from tests.eval_case_loader import load_management_cases_by_id


MANAGEMENT_CASES = load_management_cases_by_id()


class FakeDocument:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.id = 1
        self.title = "有給休暇の申請ルール"
        self.source = "hr_policy_v1.pdf"
        self.content = "有給休暇は社内システムから申請します。"
        self.version = "v1"
        self.is_active = True
        self.document_group = "hr_policy"
        self.access_level = "public"
        self.created_at = now
        self.updated_at = now


class FakeQuery:
    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return []


class FakeSession:
    def __init__(self, document: FakeDocument) -> None:
        self.document = document
        self.deleted_document_id: int | None = None

    def get(self, model, document_id: int):
        if self.deleted_document_id == document_id:
            return None
        if document_id == self.document.id:
            return self.document
        return None

    def query(self, model):
        return FakeQuery()

    def delete(self, document: FakeDocument) -> None:
        self.deleted_document_id = document.id

    def commit(self) -> None:
        if self.deleted_document_id is None:
            self.document.updated_at = datetime.now(timezone.utc)

    def refresh(self, document: FakeDocument) -> None:
        return None

    def close(self) -> None:
        return None


def test_patch_active_flag_affects_search(monkeypatch) -> None:
    document = FakeDocument()

    monkeypatch.setattr(main, "enable_pgvector", lambda: None)
    monkeypatch.setattr(main.Base.metadata, "create_all", lambda bind: None)
    monkeypatch.setattr(main, "SessionLocal", lambda: FakeSession(document))

    def fake_retrieve_chunks(
        db, query: str, top_k: int, user_role: str = "employee"
    ):
        if not document.is_active:
            return []
        return [
            {
                "chunk_id": 1,
                "document_id": document.id,
                "chunk_index": 0,
                "content": document.content,
                "source": document.source,
                "score": 0.8,
                "rerank_position": 1,
                "version": document.version,
                "updated_at": document.updated_at,
                "document_group": document.document_group,
            }
        ]

    monkeypatch.setattr(main, "retrieve_chunks", fake_retrieve_chunks)

    with TestClient(main.app) as client:
        search_before = client.post("/search", json={"query": "有給申請はどうやる？", "top_k": 3})
        assert search_before.status_code == 200
        assert len(search_before.json()) == 1
        assert search_before.json()[0]["source"] == "hr_policy_v1.pdf"

        patch_response = client.patch("/documents/1/active", json={"is_active": False})
        assert patch_response.status_code == 200
        patch_body = patch_response.json()
        assert patch_body["is_active"] is False
        assert patch_body["updated_at"] != patch_body["created_at"]

        search_after = client.post("/search", json={"query": "有給申請はどうやる？", "top_k": 3})
        assert search_after.status_code == 200
        assert search_after.json() == []


def test_get_document_returns_single_document(monkeypatch) -> None:
    document = FakeDocument()
    case = MANAGEMENT_CASES["META-008"]

    monkeypatch.setattr(main, "enable_pgvector", lambda: None)
    monkeypatch.setattr(main.Base.metadata, "create_all", lambda bind: None)
    monkeypatch.setattr(main, "SessionLocal", lambda: FakeSession(document))

    with TestClient(main.app) as client:
        response = client.request(case["method"], case["path"])

    assert response.status_code == case["expected_status"]
    body = response.json()
    assert body["id"] == 1
    assert body["title"] == "有給休暇の申請ルール"
    assert body["source"] == "hr_policy_v1.pdf"
    assert body["version"] == "v1"
    assert body["is_active"] is True
    assert body["document_group"] == "hr_policy"
    assert body["access_level"] == "public"


def test_delete_document_returns_204_and_removes_document(monkeypatch) -> None:
    document = FakeDocument()
    session = FakeSession(document)

    monkeypatch.setattr(main, "enable_pgvector", lambda: None)
    monkeypatch.setattr(main.Base.metadata, "create_all", lambda bind: None)
    monkeypatch.setattr(main, "SessionLocal", lambda: session)

    with TestClient(main.app) as client:
        response = client.delete("/documents/1")
        follow_up = client.get("/documents/1")

    assert response.status_code == 204
    assert response.text == ""
    assert session.deleted_document_id == 1
    assert follow_up.status_code == 404
    assert follow_up.json() == {"detail": "Document not found"}


@pytest.mark.parametrize("case_id", ["META-009", "META-011", "META-014"])
def test_management_endpoints_return_expected_missing_document_response(
    monkeypatch, case_id: str
) -> None:
    document = FakeDocument()
    case = MANAGEMENT_CASES[case_id]

    monkeypatch.setattr(main, "enable_pgvector", lambda: None)
    monkeypatch.setattr(main.Base.metadata, "create_all", lambda bind: None)
    monkeypatch.setattr(main, "SessionLocal", lambda: FakeSession(document))

    with TestClient(main.app) as client:
        response = client.request(case["method"], case["path"], json=case.get("body"))

    assert response.status_code == case["expected_status"]
    assert response.json() == {"detail": case["expected_detail"]}


def test_get_document_chunks_returns_empty_list_for_missing_document(monkeypatch) -> None:
    document = FakeDocument()

    monkeypatch.setattr(main, "enable_pgvector", lambda: None)
    monkeypatch.setattr(main.Base.metadata, "create_all", lambda bind: None)
    monkeypatch.setattr(main, "SessionLocal", lambda: FakeSession(document))

    with TestClient(main.app) as client:
        chunks_response = client.get("/documents/9999/chunks")

    assert chunks_response.status_code == 200
    assert chunks_response.json() == []


def test_create_document_rejects_invalid_access_level(monkeypatch) -> None:
    monkeypatch.setattr(main, "enable_pgvector", lambda: None)
    monkeypatch.setattr(main.Base.metadata, "create_all", lambda bind: None)

    with TestClient(main.app) as client:
        response = client.post(
            "/documents",
            json={
                "title": "就業規則",
                "source": "rules.pdf",
                "content": "本文です。",
                "document_group": "work_rules",
                "access_level": "finance",
            },
        )

    assert response.status_code == 422


def test_search_rejects_invalid_user_role(monkeypatch) -> None:
    monkeypatch.setattr(main, "enable_pgvector", lambda: None)
    monkeypatch.setattr(main.Base.metadata, "create_all", lambda bind: None)

    with TestClient(main.app) as client:
        response = client.post(
            "/search",
            json={
                "query": "就業規則",
                "top_k": 3,
                "user_role": "finance",
            },
        )

    assert response.status_code == 422


def test_ask_rejects_top_k_over_limit(monkeypatch) -> None:
    monkeypatch.setattr(main, "enable_pgvector", lambda: None)
    monkeypatch.setattr(main.Base.metadata, "create_all", lambda bind: None)

    with TestClient(main.app) as client:
        response = client.post(
            "/ask",
            json={
                "query": "就業規則",
                "top_k": 99,
                "user_role": "employee",
            },
        )

    assert response.status_code == 422
