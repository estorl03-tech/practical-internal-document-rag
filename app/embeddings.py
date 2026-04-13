import os

from openai import OpenAI

EMBEDDING_MODEL = "text-embedding-3-small"

def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def embed_text(text: str) -> list[float]:
    client = get_client()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding

CHAT_MODEL = "gpt-5.4-nano"


def generate_answer(query: str, context: str) -> str:
    client = get_client()
    response = client.responses.create(
        model=CHAT_MODEL,
        input=[
            {
                "role": "system",
                "content": (
                    "あなたは企業内ナレッジ検索アシスタントです。"
                    "提供された context の範囲だけを使って回答してください。"
                    "回答は必ず次の方針に従ってください。"

                    "1. まず質問に対する結論を、簡潔に述べてください。"
                    "2. 次に、その結論の根拠となる情報を context に基づいて短く示してください。"
                    "3. 質問に関連する重要な補足がある場合のみ、短く付け加えてください。"
                    "4. context に書かれていない内容は補完しないでください。"
                    "5. 情報が不足している場合は、その旨を明示してください。"

                    "回答は自然な日本語で、簡潔にまとめてください。"
                    "回答の冒頭は、見出しを付けずに自然な文章で結論を書いてください。"
                    "見出しを使う場合は「根拠」「補足」のみを使い、「context」という語は使わないでください。"
                    "ユーザー向けの簡潔で読みやすい文体にしてください。"

                    "回答フォーマットはできるだけ次に従ってください。"
                    "- 1行目は見出しなしで結論を書く"
                    "- その後に「根拠」という見出しを置き、箇条書きで示す"
                    "- 補足がある場合のみ「補足」という見出しを置き、箇条書きで示す"
                    "- 見出しは「根拠」「補足」のみを使う"
                    "- 「【】」や過度な装飾は使わない"
                    "補足では『context』という語を使わず、『文書』または『提示された情報』と言い換えてください。"


                ),
            },
            {
                "role": "user",
                "content": f"Question: {query}\n\nContext:\n{context}",
            },
        ],
    )
    return response.output_text
