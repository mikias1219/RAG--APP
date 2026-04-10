from django.contrib import admin

from .models import DocumentCollection, IndexedDocument


@admin.register(DocumentCollection)
class DocumentCollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "slug", "updated_at")
    list_filter = ("user",)
    search_fields = ("name", "slug", "user__username")


@admin.register(IndexedDocument)
class IndexedDocumentAdmin(admin.ModelAdmin):
    list_display = ("original_name", "user", "collection", "chunk_count", "uploaded_at")
    list_filter = ("user", "collection")
    search_fields = ("original_name",)
