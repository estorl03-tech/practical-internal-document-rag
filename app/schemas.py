from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AccessLevel = Literal["public", "hr"]
UserRole = Literal["employee", "hr"]


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class DocumentCreate(StrictBaseModel):
    title: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=20000)
    version: str = Field(default="v1", min_length=1, max_length=20)
    is_active: bool = True
    document_group: str = Field(min_length=1, max_length=100)
    access_level: AccessLevel = "public"


class DocumentRead(StrictBaseModel):
    id: int
    title: str
    source: str
    content: str
    version: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    document_group: str
    access_level: AccessLevel

    model_config = {"from_attributes": True}


class DocumentActiveUpdate(StrictBaseModel):
    is_active: bool


class DocumentUpdate(StrictBaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    source: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1, max_length=20000)
    version: str | None = Field(default=None, min_length=1, max_length=20)
    is_active: bool | None = None
    document_group: str | None = Field(default=None, min_length=1, max_length=100)
    access_level: AccessLevel | None = None


class DocumentChunkRead(StrictBaseModel):
    id: int
    document_id: int
    chunk_index: int
    content: str
    source: str

    model_config = {"from_attributes": True}


class SearchRequest(StrictBaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=3, ge=1, le=10)
    user_role: UserRole = "employee"


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


class AskRequest(StrictBaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=3, ge=1, le=10)
    user_role: UserRole = "employee"


class AskResponse(BaseModel):
    answer: str
    sources: list[SearchResult]
    used_sources: list[SearchResult]
    confidence: float
    enough_information: bool
    answer_level: str
    used_source_summaries: list[str]
