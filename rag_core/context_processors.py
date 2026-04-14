"""Template context for the authenticated app shell."""

from __future__ import annotations

from django.conf import settings

from rag_core.models import DocumentCollection, OrganizationMember


def app_shell(request):
    ctx = {"sidebar_collections": [], "active_org": None}
    if request.user.is_authenticated:
        member = (
            OrganizationMember.objects.select_related("organization")
            .filter(user=request.user)
            .order_by("organization__name")
            .first()
        )
        if member:
            ctx["active_org"] = member.organization
            ctx["sidebar_collections"] = DocumentCollection.objects.filter(
                organization=member.organization
            )[:50]
    return ctx


def feature_flags(_request):
    return {
        "oidc_enabled": bool(
            settings.OIDC_RP_CLIENT_ID
            and settings.OIDC_OP_AUTHORIZATION_ENDPOINT
            and settings.OIDC_OP_TOKEN_ENDPOINT
        )
    }
