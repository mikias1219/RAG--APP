"""Azure AI Search: vector + keyword hybrid retrieval."""

from __future__ import annotations

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
    results = client.search(
        search_text=query_text or "*",
        vector_queries=[vector_query],
        filter=filter_expr,
        select=["id", "title", "content", "source", "chunkIndex", "userId", "collectionId"],
        top=top,
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
    client.merge_or_upload_documents(documents)


def delete_documents(document_ids: list[str]) -> None:
    """Remove chunks from the index by id."""
    if not document_ids:
        return
    client = _search_client()
    client.delete_documents(documents=[{"id": i} for i in document_ids])
