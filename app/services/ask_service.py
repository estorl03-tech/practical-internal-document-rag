from sqlalchemy.orm import Session

from app.embeddings import generate_answer
from app.schemas import AskResponse, SearchResult
from app.services.search_service import retrieve_chunks

GREEN_TOP1_THRESHOLD = 0.65
GREEN_TOP2_THRESHOLD = 0.55
RED_TOP1_THRESHOLD = 0.50


def answer_question(
    db: Session, query: str, top_k: int, user_role: str = "employee"
) -> AskResponse:
    sources = retrieve_chunks(db, query=query, top_k=top_k, user_role=user_role)
    answer_sources = sources[:2]

    top1_score = answer_sources[0].score if len(answer_sources) >= 1 else 0.0
    top2_score = answer_sources[1].score if len(answer_sources) >= 2 else 0.0

    confidence = (
        sum(source.score for source in answer_sources) / len(answer_sources)
        if answer_sources
        else 0.0
    )

    if top1_score >= GREEN_TOP1_THRESHOLD and top2_score >= GREEN_TOP2_THRESHOLD:
        answer_level = "green"
    elif top1_score >= RED_TOP1_THRESHOLD:
        answer_level = "yellow"
    else:
        answer_level = "red"

    enough_information = answer_level != "red"

    if not enough_information:
        return AskResponse(
            answer="十分な情報が見つからなかったため、現時点では回答できません。",
            sources=sources,
            used_sources=[],
            confidence=confidence,
            enough_information=False,
            answer_level="red",
            used_source_summaries=[],
        )

    context = build_context(answer_sources)
    answer = generate_answer(query, context)

    if answer_level == "yellow":
        answer = (
            "提示された情報だけでは断定できませんが、現時点では次のように考えられます。\n\n"
            + answer
        )

    return AskResponse(
        answer=answer,
        sources=sources,
        used_sources=answer_sources,
        confidence=confidence,
        enough_information=True,
        answer_level=answer_level,
        used_source_summaries=build_source_summaries(answer_sources),
    )


def build_context(sources: list[SearchResult]) -> str:
    context_parts = [
        f"[source: {source.source} / chunk: {source.chunk_index}]\n{source.content}"
        for source in sources
    ]
    return "\n\n".join(context_parts)


def build_source_summaries(sources: list[SearchResult]) -> list[str]:
    summaries: list[str] = []
    seen: set[str] = set()

    for source in sources:
        updated_date = source.updated_at.strftime("%Y-%m-%d")
        summary = f"{source.source} ({source.version}, {updated_date}更新)"
        if summary not in seen:
            summaries.append(summary)
            seen.add(summary)

    return summaries
