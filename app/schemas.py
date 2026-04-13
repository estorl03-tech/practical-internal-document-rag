from datetime import datetime

from pydantic import BaseModel


class DocumentCreate(BaseModel):
    title: str
    source: str
    content: str
    version: str = "v1"
    is_active: bool = True
    document_group: str
    access_level: str = "public"


class DocumentRead(BaseModel):
    id: int
    title: str
    source: str
    content: str
    version: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    document_group: str
    access_level: str

    model_config = {"from_attributes": True}


class DocumentActiveUpdate(BaseModel):
    is_active: bool


class DocumentUpdate(BaseModel):
    title: str | None = None
    source: str | None = None
    content: str | None = None
    version: str | None = None
    is_active: bool | None = None
    document_group: str | None = None
    access_level: str | None = None


class DocumentChunkRead(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    content: str
    source: str

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    query: str
    top_k: int = 3
    user_role: str = "employee"


class SearchResult(BaseModel):
    chunk_id: int
    document_id: int
    chunk_index: int
    content: str
    source: str
    score: float
    rerank_position: int | None = None
    version: str
    updated_at: datetime
    document_group: str


class AskRequest(BaseModel):
    query: str
    top_k: int = 3
    user_role: str = "employee"


class AskResponse(BaseModel):
    answer: str
    sources: list[SearchResult]
    used_sources: list[SearchResult]
    confidence: float
    enough_information: bool
    answer_level: str
    used_source_summaries: list[str]
