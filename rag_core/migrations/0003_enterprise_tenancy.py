import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def bootstrap_organizations(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Organization = apps.get_model("rag_core", "Organization")
    OrganizationMember = apps.get_model("rag_core", "OrganizationMember")
    DocumentCollection = apps.get_model("rag_core", "DocumentCollection")
    IndexedDocument = apps.get_model("rag_core", "IndexedDocument")

    for user in User.objects.all():
        slug = f"{user.username}-team"
        org, _ = Organization.objects.get_or_create(
            owner_id=user.id,
            defaults={"name": f"{user.username} Team", "slug": slug, "plan": "free"},
        )
        OrganizationMember.objects.get_or_create(
            organization_id=org.id,
            user_id=user.id,
            defaults={"role": "owner"},
        )
        DocumentCollection.objects.filter(user_id=user.id).update(organization_id=org.id)
        IndexedDocument.objects.filter(user_id=user.id).update(organization_id=org.id)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("rag_core", "0002_multiuser_collections"),
    ]

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=220)),
                ("slug", models.SlugField(max_length=240, unique=True)),
                (
                    "plan",
                    models.CharField(
                        choices=[("free", "Free"), ("pro", "Pro"), ("enterprise", "Enterprise")],
                        default="free",
                        max_length=32,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="owned_organizations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="OrganizationMember",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "role",
                    models.CharField(
                        choices=[("owner", "Owner"), ("admin", "Admin"), ("editor", "Editor"), ("viewer", "Viewer")],
                        default="viewer",
                        max_length=32,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to="rag_core.organization",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="organization_memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="documentcollection",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="collections",
                to="rag_core.organization",
            ),
        ),
        migrations.AddField(
            model_name="indexeddocument",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="documents",
                to="rag_core.organization",
            ),
        ),
        migrations.CreateModel(
            name="UsageLedger",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("metric", models.CharField(choices=[("question", "question"), ("upload", "upload"), ("token", "token")], max_length=32)),
                ("amount", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="usage_events",
                        to="rag_core.organization",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="usage_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.RunPython(bootstrap_organizations, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="documentcollection",
            name="rag_core_documentcollection_user_slug_uniq",
        ),
        migrations.AddConstraint(
            model_name="documentcollection",
            constraint=models.UniqueConstraint(
                fields=("organization", "slug"),
                name="rag_core_documentcollection_org_slug_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="organizationmember",
            constraint=models.UniqueConstraint(
                fields=("organization", "user"),
                name="rag_core_orgmember_org_user_uniq",
            ),
        ),
    ]
