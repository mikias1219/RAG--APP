"""Token-aware text chunking for RAG."""

from __future__ import annotations

import tiktoken


def get_encoder():
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    """
    Split text into overlapping chunks by token count (approximate if tiktoken missing).
    """
    text = text.strip()
    if not text:
        return []

    enc = get_encoder()
    if enc is None:
        # Fallback: rough char split (~4 chars per token)
        approx = max(chunk_size * 4, 100)
        ov = max(overlap * 4, 0)
        chunks = []
        i = 0
        while i < len(text):
            chunks.append(text[i : i + approx])
            i += approx - ov
        return [c for c in chunks if c.strip()]

    tokens = enc.encode(text)
    if len(tokens) <= chunk_size:
        return [enc.decode(tokens)]

    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(enc.decode(chunk_tokens))
        if end >= len(tokens):
            break
        start = end - overlap
        if start < 0:
            start = 0
    return chunks
