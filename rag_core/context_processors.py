"""Template context for the authenticated app shell."""

from __future__ import annotations

from rag_core.models import DocumentCollection


def app_shell(request):
    ctx = {"sidebar_collections": []}
    if request.user.is_authenticated:
        ctx["sidebar_collections"] = DocumentCollection.objects.filter(user=request.user)[:50]
    return ctx
