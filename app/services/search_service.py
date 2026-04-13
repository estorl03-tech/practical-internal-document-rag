from sqlalchemy import select
from sqlalchemy.orm import Session

from app.embeddings import embed_text
from app.models import Document, DocumentChunk
from app.schemas import SearchResult
from app.services.query_service import rewrite_query
from app.services.rerank_service import rerank_chunks

HYBRID_VECTOR_WEIGHT = 0.7
HYBRID_LEXICAL_WEIGHT = 0.3
HYBRID_CANDIDATE_MULTIPLIER = 5
HYBRID_MIN_CANDIDATES = 10
TITLE_MATCH_BONUS = 0.03


def normalize_text(text: str) -> str:
    return "".join(text.lower().split())


def retrieve_chunks(
    db: Session,
    query: str,
    top_k: int,
    user_role: str = "employee",
) -> list[SearchResult]:
    candidate_k = max(top_k * HYBRID_CANDIDATE_MULTIPLIER, HYBRID_MIN_CANDIDATES)

    rewritten_query = rewrite_query(query)
    query_embedding = embed_text(rewritten_query)
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)

    statement = (
        select(DocumentChunk, distance.label("distance"))
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(Document.is_active.is_(True))
        .order_by(distance)
        .limit(candidate_k)
    )

    rows = db.execute(statement).all()

    scored_results: list[tuple[DocumentChunk, float]] = []
    for chunk, distance_value in rows:
        if not can_access(chunk.document.access_level, user_role):
            continue

        vector_score = 1 - float(distance_value)
        lexical_text = f"タイトル: {chunk.document.title}\n本文: {chunk.content}"
        keyword_score = lexical_score(rewritten_query, lexical_text)
        hybrid_score = (
            HYBRID_VECTOR_WEIGHT * vector_score + HYBRID_LEXICAL_WEIGHT * keyword_score
        )
        hybrid_score += title_match_bonus(rewritten_query, chunk.document.title)

        scored_results.append((chunk, hybrid_score))

    scored_results.sort(key=lambda item: item[1], reverse=True)

    results: list[SearchResult] = []
    for chunk, hybrid_score in scored_results:
        results.append(
            SearchResult(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                source=chunk.source,
                score=hybrid_score,
                version=chunk.document.version,
                updated_at=chunk.document.updated_at,
                document_group=chunk.document.document_group,
            )
        )

    results = keep_latest_by_document_group(results)
    results = rerank_chunks(query, results)
    results = results[:top_k]

    for position, result in enumerate(results, start=1):
        result.rerank_position = position

    return results


def make_bigrams(text: str) -> set[str]:
    normalized = normalize_text(text)
    if len(normalized) < 2:
        return {normalized} if normalized else set()
    return {normalized[i : i + 2] for i in range(len(normalized) - 1)}


def lexical_score(query: str, content: str) -> float:
    query_bigrams = make_bigrams(query)
    content_bigrams = make_bigrams(content)

    if not query_bigrams or not content_bigrams:
        return 0.0

    overlap = query_bigrams & content_bigrams
    return len(overlap) / len(query_bigrams)


def title_match_bonus(query: str, title: str) -> float:
    query_bigrams = make_bigrams(query)
    title_bigrams = make_bigrams(title)

    if not query_bigrams or not title_bigrams:
        return 0.0

    overlap_ratio = len(query_bigrams & title_bigrams) / len(query_bigrams)
    if overlap_ratio >= 0.15:
        return TITLE_MATCH_BONUS

    return 0.0


def version_rank(version: str) -> int:
    normalized = version.lower().strip()
    if normalized.startswith("v") and normalized[1:].isdigit():
        return int(normalized[1:])
    return 0


def keep_latest_by_document_group(results: list[SearchResult]) -> list[SearchResult]:
    latest_document_by_group: dict[str, SearchResult] = {}

    for result in results:
        existing = latest_document_by_group.get(result.document_group)
        if existing is None:
            latest_document_by_group[result.document_group] = result
            continue

        if result.updated_at > existing.updated_at:
            latest_document_by_group[result.document_group] = result
            continue

        if result.updated_at == existing.updated_at and version_rank(
            result.version
        ) > version_rank(existing.version):
            latest_document_by_group[result.document_group] = result

    latest_document_ids = {
        result.document_id for result in latest_document_by_group.values()
    }

    return [result for result in results if result.document_id in latest_document_ids]


def can_access(access_level: str, user_role: str) -> bool:
    if access_level == "public":
        return True
    return access_level == user_role
