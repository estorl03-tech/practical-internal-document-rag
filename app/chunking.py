def split_long_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start += step

    return chunks


def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n") if paragraph.strip()]
    chunks: list[str] = []

    for paragraph in paragraphs:
        if len(paragraph) <= chunk_size:
            chunks.append(paragraph)
        else:
            chunks.extend(split_long_text(paragraph, chunk_size=chunk_size, overlap=overlap))

    return chunks
