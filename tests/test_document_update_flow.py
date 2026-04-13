from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app import main
from tests.eval_case_loader import load_management_cases_by_id


MANAGEMENT_CASES = load_management_cases_by_id()


class FakeChunk:
    def __init__(self, chunk_index: int, content: str, source: str) -> None:
        self.chunk_index = chunk_index
        self.content = content
        self.source = source


class FakeDocument:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.id = 1
        self.title = "旧タイトル"
        self.source = "old.pdf"
        self.content = "旧本文"
        self.version = "v1"
        self.is_active = True
        self.document_group = "old_policy"
        self.access_level = "public"
        self.created_at = now
        self.updated_at = now
        self.chunks = [FakeChunk(0, "旧本文", "old.pdf")]


class FakeSession:
    def __init__(self, document: FakeDocument) -> None:
        self.document = document

    def get(self, model, document_id: int):
        if document_id == self.document.id:
            return self.document
        return None

    def commit(self) -> None:
        self.document.updated_at = datetime.now(timezone.utc)

    def refresh(self, document: FakeDocument) -> None:
        return None

    def close(self) -> None:
        return None


def test_patch_document_rebuilds_chunks_when_search_fields_change(monkeypatch) -> None:
    document = FakeDocument()
    embedded_inputs: list[str] = []

    monkeypatch.setattr(main, "enable_pgvector", lambda: None)
    monkeypatch.setattr(main.Base.metadata, "create_all", lambda bind: None)
    monkeypatch.setattr(main, "SessionLocal", lambda: FakeSession(document))
    monkeypatch.setattr(
        main,
        "chunk_text",
        lambda text, chunk_size=300, overlap=50: ["更新本文-1", "更新本文-2"],
    )
    monkeypatch.setattr(
        main,
        "embed_text",
        lambda text: embedded_inputs.append(text) or [0.1, 0.2],
    )

    with TestClient(main.app) as client:
        response = client.patch(
            "/documents/1",
            json={
                "title": "新タイトル",
                "source": "new.pdf",
                "content": "更新本文",
                "version": "v2",
                "is_active": False,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "新タイトル"
    assert body["source"] == "new.pdf"
    assert body["content"] == "更新本文"
    assert body["version"] == "v2"
    assert body["is_active"] is False
    assert body["document_group"] == "old_policy"
    assert body["access_level"] == "public"
    assert body["updated_at"] != body["created_at"]

    assert len(document.chunks) == 2
    assert document.chunks[0].content == "更新本文-1"
    assert document.chunks[0].source == "new.pdf"
    assert document.chunks[1].content == "更新本文-2"
    assert document.chunks[1].source == "new.pdf"
    assert embedded_inputs == [
        "タイトル: 新タイトル\n本文: 更新本文-1",
        "タイトル: 新タイトル\n本文: 更新本文-2",
    ]


def test_patch_document_returns_404_for_missing_document(monkeypatch) -> None:
    document = FakeDocument()
    case = MANAGEMENT_CASES["META-010"]

    monkeypatch.setattr(main, "enable_pgvector", lambda: None)
    monkeypatch.setattr(main.Base.metadata, "create_all", lambda bind: None)
    monkeypatch.setattr(main, "SessionLocal", lambda: FakeSession(document))

    with TestClient(main.app) as client:
        response = client.request(case["method"], case["path"], json=case["body"])

    assert response.status_code == case["expected_status"]
    assert response.json() == {"detail": case["expected_detail"]}
