import io
import re

from pypdf import PdfReader


def extract_text_from_pdf_bytes(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []

    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text.strip())

    raw_text = "\n".join(parts).strip()
    return normalize_extracted_pdf_text(raw_text)


def normalize_extracted_pdf_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    # 行頭・行末の余分な空白を落とす
    lines = [line.strip() for line in normalized.split("\n")]

    # 空行は1行にまとめる
    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)

    # 日本語1文字ごとの不自然な空白を潰す
    normalized = re.sub(
        r"(?<=[\u3040-\u30ff\u4e00-\u9fff])[ \t\u3000]+(?=[\u3040-\u30ff\u4e00-\u9fff])",
        "",
        normalized,
    )

    # 日本語文字どうしの不自然な改行を潰す
    normalized = re.sub(
        r"(?<=[\u3040-\u30ff\u4e00-\u9fff])\n(?=[\u3040-\u30ff\u4e00-\u9fff])",
        "",
        normalized,
    )

    # 全角記号の前後にある不自然な空白を少し詰める
    normalized = re.sub(r"\s+([。、（）「」：])", r"\1", normalized)
    normalized = re.sub(r"([（「])\s+", r"\1", normalized)

    return normalized.strip()
