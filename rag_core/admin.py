from django.contrib import admin

from .models import IndexedDocument


@admin.register(IndexedDocument)
class IndexedDocumentAdmin(admin.ModelAdmin):
    list_display = ("original_name", "uploaded_at")
    search_fields = ("original_name",)
