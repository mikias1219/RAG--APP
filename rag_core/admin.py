from django.contrib import admin

from .models import (
    DocumentCollection,
    IndexedDocument,
    Organization,
    OrganizationMember,
    UsageLedger,
)


@admin.register(DocumentCollection)
class DocumentCollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "user", "slug", "updated_at")
    list_filter = ("organization", "user")
    search_fields = ("name", "slug", "user__username", "organization__name")


@admin.register(IndexedDocument)
class IndexedDocumentAdmin(admin.ModelAdmin):
    list_display = ("original_name", "organization", "user", "collection", "chunk_count", "uploaded_at")
    list_filter = ("organization", "user", "collection")
    search_fields = ("original_name",)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "plan", "owner", "created_at")
    search_fields = ("name", "slug", "owner__username")


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "role", "created_at")
    list_filter = ("organization", "role")


@admin.register(UsageLedger)
class UsageLedgerAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "metric", "amount", "created_at")
    list_filter = ("organization", "metric")
