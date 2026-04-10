from django.contrib.auth.models import User
from django.db import models
from django.utils.text import slugify


class DocumentCollection(models.Model):
    """A user's knowledge base (documents are indexed into Azure Search with this id)."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="document_collections",
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "slug"],
                name="rag_core_documentcollection_user_slug_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.user.username})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self._ensure_unique_slug()
        super().save(*args, **kwargs)

    def _ensure_unique_slug(self) -> None:
        base = slugify(self.name)[:180] or "collection"
        for n in range(0, 500):
            cand = base if n == 0 else f"{base}-{n}"
            qs = DocumentCollection.objects.filter(user_id=self.user_id, slug=cand)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if not qs.exists():
                self.slug = cand
                return
        self.slug = f"{base}-{self.pk or 'new'}"


class IndexedDocument(models.Model):
    """Record of an uploaded file; search chunks reference the same user/collection in Azure."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="indexed_documents",
    )
    collection = models.ForeignKey(
        DocumentCollection,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    original_name = models.CharField(max_length=512)
    stored_path = models.CharField(max_length=1024)
    chunk_count = models.PositiveIntegerField(default=0)
    search_document_ids = models.JSONField(default=list)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return self.original_name
