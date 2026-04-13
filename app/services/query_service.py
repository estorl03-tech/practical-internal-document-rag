from app.embeddings import CHAT_MODEL, get_client

def rewrite_query(query: str) -> str:
    client = get_client()

    system_prompt = (
        "あなたは企業内ナレッジ検索向けのクエリ書き換えアシスタントです。"
        "ユーザーの質問を、意味を変えずに、検索しやすい短い日本語クエリに書き換えてください。"
        "口語表現は、検索に適した自然な表現へ整えてください。"
        "回答は検索クエリ1つだけを返してください。"
        "説明、補足、箇条書き、引用符は不要です。"
    )

    response = client.responses.create(
        model=CHAT_MODEL,
        input=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": query,
            },
        ],
    )

    rewritten_query = response.output_text.strip()
    return rewritten_query or query