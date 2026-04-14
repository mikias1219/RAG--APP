"""High-level RAG orchestration."""

from __future__ import annotations

import re
from uuid import uuid4

from django.conf import settings

from . import azure_openai, azure_search


def _chunk_doc_id(
    organization_id: int,
    collection_id: int,
    source_name: str,
    chunk_index: int,
    document_uid: str,
) -> str:
    """
    Azure Search document keys: letters, digits, dash, underscore, equals (no dots).
    Scoped per user and collection to avoid collisions.
    """
    base = re.sub(r"[^a-zA-Z0-9_=.-]", "_", source_name)
    base = base.replace(".", "_")[:80]
    return f"o{organization_id}_c{collection_id}_{document_uid}_{base}_{chunk_index}"


SYSTEM_PROMPT = (
    "You are a precise enterprise assistant. Answer using ONLY the supplied context. "
    "If the answer is not supported by the context, say so. Keep answers concise and actionable. "
    "When citing, mention the document name or title."
)


def _search_filter_for_user(organization_id: int, collection_id: int | None) -> str:
    # OData: strings in single quotes; escape single quotes by doubling
    uid = str(organization_id).replace("'", "''")
    if collection_id is None:
        return f"organizationId eq '{uid}'"
    cid = str(collection_id).replace("'", "''")
    return f"organizationId eq '{uid}' and collectionId eq '{cid}'"


def answer_question(
    question: str,
    user_id: int,
    organization_id: int,
    collection_id: int | None = None,
    top_k: int = 5,
) -> tuple[str, list[dict]]:
    q = question.strip()
    if not q:
        return "", []

    filt = _search_filter_for_user(organization_id, collection_id)
    vec = azure_openai.embed_query(q)
    hits = azure_search.hybrid_search(q, vec, top=top_k, filter_expr=filt)
    if not hits:
        # Fallback to lexical-only search when vector retrieval is unavailable.
        hits = azure_search.keyword_search(q, top=top_k, filter_expr=filt)
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
                "collectionId": h.get("collectionId"),
            }
        )

    if not chunks:
        return (
            "No matching passages were found in your indexed documents for this workspace. "
            "Upload files to this collection (or switch scope) and try again.",
            [],
        )

    answer = azure_openai.chat_with_context(SYSTEM_PROMPT, q, chunks)
    return answer, sources


def index_file_content(
    text: str,
    source_name: str,
    *,
    user_id: int,
    organization_id: int,
    collection_id: int,
    title: str | None = None,
    previous_document_ids: list[str] | None = None,
) -> tuple[int, list[str]]:
    """Chunk, embed, push to Azure Search. Returns (chunk_count, search document ids)."""
    from .chunking import chunk_text

    display_title = title or source_name
    chunks = chunk_text(
        text,
        chunk_size=settings.CHUNK_SIZE,
        overlap=settings.CHUNK_OVERLAP,
    )
    if not chunks:
        return 0, []

    embeddings = azure_openai.embed_texts(chunks)
    document_uid = uuid4().hex[:12]
    doc_ids: list[str] = []
    docs: list[dict] = []
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        doc_id = _chunk_doc_id(organization_id, collection_id, source_name, i, document_uid)
        doc_ids.append(doc_id)
        docs.append(
            {
                "id": doc_id,
                "title": display_title,
                "content": chunk,
                "source": source_name,
                "chunkIndex": i,
                "contentVector": emb,
                "userId": str(user_id),
                "organizationId": str(organization_id),
                "collectionId": str(collection_id),
                "documentUid": document_uid,
            }
        )
    if previous_document_ids:
        azure_search.delete_documents(previous_document_ids)
    azure_search.upload_documents(docs)
    return len(docs), doc_ids


def remove_document_vectors(document_ids: list[str]) -> None:
    azure_search.delete_documents(document_ids)


def healthcheck_dependencies() -> None:
    azure_openai.healthcheck()
    azure_search.healthcheck()
