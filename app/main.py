from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.chunking import chunk_text
from app.database import SessionLocal, enable_pgvector, engine
from app.embeddings import EMBEDDING_MODEL, embed_text
from app.models import Base, Document, DocumentChunk
from app.schemas import (
    AccessLevel,
    AskRequest,
    AskResponse,
    DocumentActiveUpdate,
    DocumentChunkRead,
    DocumentCreate,
    DocumentRead,
    DocumentUpdate,
    SearchRequest,
    SearchResult,
)
from app.services.ask_service import answer_question
from app.services.document_ingest_service import extract_text_from_pdf_bytes
from app.services.search_service import retrieve_chunks

MAX_PDF_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_PDF_MEDIA_TYPES = {"application/pdf"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    enable_pgvector()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Business RAG API", lifespan=lifespan)


def build_document_chunks(
    document_id: int,
    title: str,
    source: str,
    content: str,
) -> list[DocumentChunk]:
    chunks = chunk_text(content, chunk_size=300, overlap=50)
    db_chunks: list[DocumentChunk] = []

    for index, chunk in enumerate(chunks):
        retrieval_text = f"タイトル: {title}\n本文: {chunk}"
        db_chunks.append(
            DocumentChunk(
                document_id=document_id,
                chunk_index=index,
                content=chunk,
                source=source,
                embedding_model=EMBEDDING_MODEL,
                embedding=embed_text(retrieval_text),
            )
        )

    return db_chunks


def save_document(
    db: Session,
    *,
    title: str,
    source: str,
    content: str,
    version: str,
    is_active: bool,
    document_group: str,
    access_level: str,
) -> Document:
    db_document = Document(
        title=title,
        source=source,
        content=content,
        version=version,
        is_active=is_active,
        document_group=document_group,
        access_level=access_level,
    )
    db.add(db_document)
    db.flush()

    db_document.chunks = build_document_chunks(
        document_id=db_document.id,
        title=title,
        source=source,
        content=content,
    )

    db.commit()
    db.refresh(db_document)
    return db_document


def sanitize_source_filename(filename: str | None) -> str:
    if not filename:
        return "uploaded.pdf"
    safe_name = Path(filename).name
    return safe_name or "uploaded.pdf"


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/db-health")
def db_health_check() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {"status": "db ok"}


@app.get("/demo")
def demo_page() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.post("/documents", response_model=DocumentRead)
def create_document(document: DocumentCreate) -> Document:
    db: Session = SessionLocal()
    try:
        return save_document(
            db,
            title=document.title,
            source=document.source,
            content=document.content,
            version=document.version,
            is_active=document.is_active,
            document_group=document.document_group,
            access_level=document.access_level,
        )
    finally:
        db.close()


@app.get("/documents", response_model=list[DocumentRead])
def list_documents() -> list[Document]:
    db: Session = SessionLocal()
    try:
        documents = db.query(Document).order_by(Document.id).all()
        return documents
    finally:
        db.close()


@app.get("/documents/{document_id}", response_model=DocumentRead)
def get_document(document_id: int) -> Document:
    db: Session = SessionLocal()
    try:
        db_document = db.get(Document, document_id)
        if db_document is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return db_document
    finally:
        db.close()


@app.patch("/documents/{document_id}/active", response_model=DocumentRead)
def update_document_active(
    document_id: int,
    payload: DocumentActiveUpdate,
) -> Document:
    db: Session = SessionLocal()
    try:
        db_document = db.get(Document, document_id)
        if db_document is None:
            raise HTTPException(status_code=404, detail="Document not found")

        db_document.is_active = payload.is_active
        db.commit()
        db.refresh(db_document)
        return db_document
    finally:
        db.close()


@app.patch("/documents/{document_id}", response_model=DocumentRead)
def update_document(
    document_id: int,
    payload: DocumentUpdate,
) -> Document:
    db: Session = SessionLocal()
    try:
        db_document = db.get(Document, document_id)
        if db_document is None:
            raise HTTPException(status_code=404, detail="Document not found")

        updates = payload.model_dump(exclude_unset=True)
        rebuild_chunks = False

        if "title" in updates and updates["title"] != db_document.title:
            db_document.title = updates["title"]
            rebuild_chunks = True
        if "source" in updates and updates["source"] != db_document.source:
            db_document.source = updates["source"]
            rebuild_chunks = True
        if "content" in updates and updates["content"] != db_document.content:
            db_document.content = updates["content"]
            rebuild_chunks = True
        if "version" in updates:
            db_document.version = updates["version"]
        if "is_active" in updates:
            db_document.is_active = updates["is_active"]
        if "access_level" in updates:
            db_document.access_level = updates["access_level"]
        if "document_group" in updates:
            db_document.document_group = updates["document_group"]

        if rebuild_chunks:
            db_document.chunks = build_document_chunks(
                document_id=db_document.id,
                title=db_document.title,
                source=db_document.source,
                content=db_document.content,
            )

        db.commit()
        db.refresh(db_document)
        return db_document
    finally:
        db.close()


@app.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int) -> Response:
    db: Session = SessionLocal()
    try:
        db_document = db.get(Document, document_id)
        if db_document is None:
            raise HTTPException(status_code=404, detail="Document not found")

        db.delete(db_document)
        db.commit()
        return Response(status_code=204)
    finally:
        db.close()


@app.get("/documents/{document_id}/chunks", response_model=list[DocumentChunkRead])
def get_document_chunks(document_id: int) -> list[DocumentChunk]:
    db: Session = SessionLocal()
    try:
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .all()
        )
        return chunks
    finally:
        db.close()


@app.post("/search", response_model=list[SearchResult])
def search_chunks(request: SearchRequest) -> list[SearchResult]:
    db: Session = SessionLocal()
    try:
        return retrieve_chunks(
            db,
            query=request.query,
            top_k=request.top_k,
            user_role=request.user_role,
        )
    finally:
        db.close()


@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest) -> AskResponse:
    db: Session = SessionLocal()
    try:
        return answer_question(
            db,
            query=request.query,
            top_k=request.top_k,
            user_role=request.user_role,
        )
    finally:
        db.close()


@app.post("/documents/upload/pdf", response_model=DocumentRead)
def upload_pdf_document(
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=200),
    version: str = Form("v1", min_length=1, max_length=20),
    is_active: bool = Form(True),
    document_group: str = Form(..., min_length=1, max_length=100),
    access_level: AccessLevel = Form("public"),
) -> Document:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF file is required")
    if file.content_type and file.content_type not in ALLOWED_PDF_MEDIA_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported PDF media type")

    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(data) > MAX_PDF_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file is too large")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Invalid PDF file")

    content = extract_text_from_pdf_bytes(data)
    if not content.strip():
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from PDF",
        )

    db: Session = SessionLocal()
    try:
        return save_document(
            db,
            title=title,
            source=sanitize_source_filename(file.filename),
            content=content,
            version=version,
            is_active=is_active,
            document_group=document_group,
            access_level=access_level,
        )
    finally:
        db.close()
