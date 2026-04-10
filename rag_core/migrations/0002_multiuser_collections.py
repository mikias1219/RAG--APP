# Generated manually: replace flat IndexedDocument with per-user collections.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("rag_core", "0001_initial"),
    ]

    operations = [
        migrations.DeleteModel(name="IndexedDocument"),
        migrations.CreateModel(
            name="DocumentCollection",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200)),
                ("slug", models.SlugField(blank=True, max_length=220)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="document_collections",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="IndexedDocument",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("original_name", models.CharField(max_length=512)),
                ("stored_path", models.CharField(max_length=1024)),
                ("chunk_count", models.PositiveIntegerField(default=0)),
                ("search_document_ids", models.JSONField(default=list)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "collection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documents",
                        to="rag_core.documentcollection",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="indexed_documents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-uploaded_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="documentcollection",
            constraint=models.UniqueConstraint(
                fields=("user", "slug"),
                name="rag_core_documentcollection_user_slug_uniq",
            ),
        ),
    ]
