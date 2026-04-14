"""Azure AI Search: vector + keyword hybrid retrieval."""

from __future__ import annotations

import time

from django.conf import settings
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery


def _search_client() -> SearchClient:
    endpoint = (settings.AZURE_SEARCH_ENDPOINT or "").rstrip("/")
    key = settings.AZURE_SEARCH_KEY or ""
    index = settings.AZURE_SEARCH_INDEX_NAME or "rag-documents"
    if not endpoint or not key:
        raise RuntimeError("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
    return SearchClient(
        endpoint=endpoint,
        index_name=index,
        credential=AzureKeyCredential(key),
    )


def hybrid_search(
    query_text: str,
    query_vector: list[float],
    top: int = 5,
    filter_expr: str | None = None,
) -> list[dict]:
    """
    Run vector search with optional OData filter (e.g. per-tenant isolation).
    """
    client = _search_client()
    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=top,
        fields="contentVector",
    )
    results = _with_retries(
        lambda: client.search(
            search_text=query_text or "*",
            vector_queries=[vector_query],
            filter=filter_expr,
            select=[
                "id",
                "title",
                "content",
                "source",
                "chunkIndex",
                "userId",
                "organizationId",
                "collectionId",
                "documentUid",
            ],
            top=top,
        )
    )
    out: list[dict] = []
    for r in results:
        out.append(
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "content": r.get("content"),
                "source": r.get("source"),
                "chunkIndex": r.get("chunkIndex"),
                "score": r.get("@search.score"),
                "collectionId": r.get("collectionId"),
            }
        )
    return out


def upload_documents(documents: list[dict]) -> None:
    client = _search_client()
    _with_retries(lambda: client.merge_or_upload_documents(documents))


def delete_documents(document_ids: list[str]) -> None:
    """Remove chunks from the index by id."""
    if not document_ids:
        return
    client = _search_client()
    _with_retries(lambda: client.delete_documents(documents=[{"id": i} for i in document_ids]))


def keyword_search(query_text: str, top: int = 5, filter_expr: str | None = None) -> list[dict]:
    client = _search_client()
    results = _with_retries(
        lambda: client.search(
            search_text=query_text or "*",
            filter=filter_expr,
            select=["id", "title", "content", "source", "chunkIndex", "collectionId"],
            top=top,
        )
    )
    out: list[dict] = []
    for r in results:
        out.append(
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "content": r.get("content"),
                "source": r.get("source"),
                "chunkIndex": r.get("chunkIndex"),
                "score": r.get("@search.score"),
                "collectionId": r.get("collectionId"),
            }
        )
    return out


def healthcheck() -> None:
    keyword_search("healthcheck", top=1)


def _with_retries(fn, *, retries: int = 3, delay_s: float = 0.8):
    last_exc = None
    for attempt in range(retries):
        try:
            return fn()
        except Exception as exc:  # pragma: no cover - network behavior
            last_exc = exc
            if attempt == retries - 1:
                break
            time.sleep(delay_s * (2**attempt))
    raise RuntimeError(f"Azure Search request failed after retries: {last_exc}") from last_exc
