from app.embeddings import CHAT_MODEL, get_client
from app.schemas import SearchResult

def rerank_chunks(query: str, candidates: list[SearchResult]) -> list[SearchResult]:
    if len(candidates) <= 1:
        return candidates

    client = get_client()

    candidate_text = []
    for index, candidate in enumerate(candidates, start=1):
        candidate_text.append(
            f"{index}. [source: {candidate.source} / chunk: {candidate.chunk_index}]\n"
            f"{candidate.content}"
        )

    prompt = "\n\n".join(candidate_text)

    response = client.responses.create(
        model=CHAT_MODEL,
        input=[
            {
                "role": "system",
                "content": (
                    "あなたは企業内文書検索の再ランキングアシスタントです。"
                    "与えられた質問に最もよく答える順に候補を並べ替えてください。"
                    "回答は候補番号をカンマ区切りで返してください。"
                    "説明や補足は不要です。"
                ),
            },
            {
                "role": "user",
                "content": f"質問:\n{query}\n\n候補:\n{prompt}",
            },
        ],
    )

    order_text = response.output_text.strip()


    try:
        order_indexes = [
            int(value.strip()) - 1
            for value in order_text.split(",")
        ]

        expected_indexes = set(range(len(candidates)))
        if set(order_indexes) != expected_indexes:
            return candidates

        reranked_candidates = [candidates[index] for index in order_indexes]
        return reranked_candidates
    except (ValueError, IndexError):
        return candidates
