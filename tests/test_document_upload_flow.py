from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app import main


class FakeSession:
    def close(self) -> None:
        return None


class FakeSavedDocument:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.id = 10
        self.title = "就業規則"
        self.source = "rules.pdf"
        self.content = "抽出された本文です。"
        self.version = "v1"
        self.is_active = True
        self.document_group = "work_rules"
        self.access_level = "public"
        self.created_at = now
        self.updated_at = now


def test_upload_pdf_document_creates_document_from_extracted_text(monkeypatch) -> None:
    saved_arguments: dict[str, object] = {}
    saved_document = FakeSavedDocument()

    monkeypatch.setattr(main, "enable_pgvector", lambda: None)
    monkeypatch.setattr(main.Base.metadata, "create_all", lambda bind: None)
    monkeypatch.setattr(main, "SessionLocal", lambda: FakeSession())
    monkeypatch.setattr(
        main,
        "extract_text_from_pdf_bytes",
        lambda data: "抽出された本文です。",
    )

    def fake_save_document(db, **kwargs):
        saved_arguments.update(kwargs)
        return saved_document

    monkeypatch.setattr(main, "save_document", fake_save_document)

    with TestClient(main.app) as client:
        response = client.post(
            "/documents/upload/pdf",
            files={"file": ("rules.pdf", b"%PDF-1.4 fake pdf bytes", "application/pdf")},
            data={
                "title": "就業規則",
                "version": "v1",
                "is_active": "true",
                "document_group": "work_rules",
                "access_level": "public",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "就業規則"
    assert body["source"] == "rules.pdf"
    assert body["content"] == "抽出された本文です。"
    assert body["document_group"] == "work_rules"
    assert body["access_level"] == "public"

    assert saved_arguments == {
        "title": "就業規則",
        "source": "rules.pdf",
        "content": "抽出された本文です。",
        "version": "v1",
        "is_active": True,
        "document_group": "work_rules",
        "access_level": "public",
    }


def test_upload_pdf_document_returns_400_for_non_pdf_file(monkeypatch) -> None:
    monkeypatch.setattr(main, "enable_pgvector", lambda: None)
    monkeypatch.setattr(main.Base.metadata, "create_all", lambda bind: None)

    with TestClient(main.app) as client:
        response = client.post(
            "/documents/upload/pdf",
            files={"file": ("notes.txt", b"plain text", "text/plain")},
            data={
                "title": "就業規則",
                "document_group": "work_rules",
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "PDF file is required"}


def test_upload_pdf_document_returns_400_for_empty_file(monkeypatch) -> None:
    monkeypatch.setattr(main, "enable_pgvector", lambda: None)
    monkeypatch.setattr(main.Base.metadata, "create_all", lambda bind: None)

    with TestClient(main.app) as client:
        response = client.post(
            "/documents/upload/pdf",
            files={"file": ("rules.pdf", b"", "application/pdf")},
            data={
                "title": "就業規則",
                "document_group": "work_rules",
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Uploaded file is empty"}


def test_upload_pdf_document_returns_400_when_text_extraction_fails(monkeypatch) -> None:
    monkeypatch.setattr(main, "enable_pgvector", lambda: None)
    monkeypatch.setattr(main.Base.metadata, "create_all", lambda bind: None)
    monkeypatch.setattr(
        main,
        "extract_text_from_pdf_bytes",
        lambda data: "",
    )

    with TestClient(main.app) as client:
        response = client.post(
            "/documents/upload/pdf",
            files={"file": ("rules.pdf", b"%PDF-1.4 fake pdf bytes", "application/pdf")},
            data={
                "title": "就業規則",
                "document_group": "work_rules",
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Could not extract text from PDF"}
