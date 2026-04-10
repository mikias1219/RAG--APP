"""
Create or update the Azure AI Search index used for vector RAG.

Usage:
  python manage.py setup_search_index
"""

from django.conf import settings
from django.core.management.base import BaseCommand
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    HnswParameters,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchableField,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)


class Command(BaseCommand):
    help = "Creates or updates Azure AI Search vector index for RAG."

    def handle(self, *args, **options):
        endpoint = (settings.AZURE_SEARCH_ENDPOINT or "").rstrip("/")
        key = settings.AZURE_SEARCH_KEY or ""
        index_name = settings.AZURE_SEARCH_INDEX_NAME or "rag-documents"
        dims = settings.EMBEDDING_DIMENSIONS

        if not endpoint or not key:
            self.stderr.write(
                "Set AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY in .env (see .env.example)."
            )
            return

        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="hnsw-config",
                    parameters=HnswParameters(
                        m=4,
                        ef_construction=400,
                        ef_search=500,
                        metric="cosine",
                    ),
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="vector-profile",
                    algorithm_configuration_name="hnsw-config",
                )
            ],
        )

        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(
                name="title",
                type=SearchFieldDataType.String,
                sortable=True,
                filterable=True,
            ),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SimpleField(
                name="source",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
            ),
            SimpleField(
                name="chunkIndex",
                type=SearchFieldDataType.Int32,
                filterable=True,
                sortable=True,
            ),
            SearchField(
                name="contentVector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=dims,
                vector_search_profile_name="vector-profile",
            ),
        ]

        index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
        client = SearchIndexClient(endpoint, AzureKeyCredential(key))
        client.create_or_update_index(index)
        self.stdout.write(self.style.SUCCESS(f"Index '{index_name}' is ready (vector dims={dims})."))
