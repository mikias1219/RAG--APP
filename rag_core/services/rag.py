"""High-level RAG orchestration."""

from __future__ import annotations

import re

from django.conf import settings

from . import azure_openai, azure_search


def _safe_doc_id(source_name: str, chunk_index: int) -> str:
    """Azure Search document keys: letters, digits, dash, underscore, equals."""
    base = re.sub(r"[^a-zA-Z0-9_=.-]", "_", source_name)[:120]
    return f"{base}_{chunk_index}"

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions using only the supplied context. "
    "Cite sources by title or filename when possible. Be concise."
)


def answer_question(question: str, top_k: int = 5) -> tuple[str, list[dict]]:
    """
    Returns (answer_text, sources_metadata).
    """
    q = question.strip()
    if not q:
        return "", []

    vec = azure_openai.embed_query(q)
    hits = azure_search.hybrid_search(q, vec, top=top_k)
    chunks = []
    sources: list[dict] = []
    for h in hits:
        content = h.get("content") or ""
        if content:
            chunks.append(content)
        sources.append(
            {
                "title": h.get("title"),
                "source": h.get("source"),
                "chunkIndex": h.get("chunkIndex"),
                "score": h.get("score"),
            }
        )

    if not chunks:
        return (
            "No matching passages were found in the search index. "
            "Upload documents and run indexing, or run: python manage.py index_documents",
            [],
        )

    answer = azure_openai.chat_with_context(SYSTEM_PROMPT, q, chunks)
    return answer, sources


def index_file_content(
    text: str,
    source_name: str,
    title: str | None = None,
) -> int:
    """
    Chunk file, embed, push to Azure Search. Returns number of chunks indexed.
    """
    from .chunking import chunk_text

    display_title = title or source_name
    chunks = chunk_text(
        text,
        chunk_size=settings.CHUNK_SIZE,
        overlap=settings.CHUNK_OVERLAP,
    )
    if not chunks:
        return 0

    embeddings = azure_openai.embed_texts(chunks)
    docs: list[dict] = []
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        doc_id = _safe_doc_id(source_name, i)
        docs.append(
            {
                "id": doc_id,
                "title": display_title,
                "content": chunk,
                "source": source_name,
                "chunkIndex": i,
                "contentVector": emb,
            }
        )
    azure_search.upload_documents(docs)
    return len(docs)
