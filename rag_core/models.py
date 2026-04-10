from django.db import models


class IndexedDocument(models.Model):
    """Optional local record of uploads (search index remains source of truth for chunks)."""

    original_name = models.CharField(max_length=512)
    stored_path = models.CharField(max_length=1024)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.original_name
