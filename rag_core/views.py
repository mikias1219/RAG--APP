from __future__ import annotations

from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import connection
from django.db.models import Count, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from django_ratelimit.decorators import ratelimit

from .forms import (
    CollectionForm,
    OrganizationForm,
    OrganizationMemberForm,
    QuestionForm,
    SignUpForm,
    UploadForm,
)
from .models import DocumentCollection, IndexedDocument, Organization, OrganizationMember
from .services import rag
from .services.tenancy import (
    enforce_limit,
    record_usage,
    user_can_edit_workspace,
    user_can_manage_org,
)
from .services.text_extract import extract_text_from_path


def health(_request: HttpRequest) -> HttpResponse:
    checks = {"db": "ok", "azure_search": "ok", "azure_openai": "ok"}
    code = 200
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        checks["db"] = "error"
        code = 503
    try:
        rag.healthcheck_dependencies()
    except Exception:
        checks["azure_search"] = "error"
        checks["azure_openai"] = "error"
        code = 503
    out = " ".join(f"{k}={v}" for k, v in checks.items())
    return HttpResponse(out, content_type="text/plain", status=code)


def landing(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "rag_core/landing.html",
        {
            "has_azure": bool(
                settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_SEARCH_ENDPOINT
            ),
        },
    )


def _active_org_for_user(user: User) -> Organization | None:
    member = (
        OrganizationMember.objects.select_related("organization")
        .filter(user=user)
        .order_by("organization__name")
        .first()
    )
    return member.organization if member else None


@require_http_methods(["GET", "POST"])
def register(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user: User = form.save()
            login(request, user)
            org = Organization.objects.create(
                name=f"{user.username} Team",
                owner=user,
                plan=settings.DEFAULT_TENANT_PLAN,
            )
            OrganizationMember.objects.create(organization=org, user=user, role="owner")
            DocumentCollection.objects.create(
                user=user,
                organization=org,
                name="General",
                description="Your default workspace. Upload documents and start asking questions.",
            )
            messages.success(request, 'Welcome! A workspace named "General" was created for you.')
            return redirect("dashboard")
    else:
        form = SignUpForm()
    return render(request, "rag_core/register.html", {"form": form})


def _chat_session_key(user_id: int, collection_part: str | None) -> str:
    part = str(collection_part) if collection_part is not None else "all"
    return f"rag_chat_u{user_id}_{part}"


def _chat_redirect_url(collection_pk: int | None) -> str:
    base = reverse("chat")
    if collection_pk is not None:
        return f"{base}?{urlencode({'collection': collection_pk})}"
    return base


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user_or_ip", rate="30/m", method=["POST"], block=True)
def chat(request: HttpRequest) -> HttpResponse:
    active_org = _active_org_for_user(request.user)
    collection_pk: int | None = None
    raw = (request.GET.get("collection") or request.POST.get("collection") or "").strip()
    if raw.isdigit():
        cid = int(raw)
        if DocumentCollection.objects.filter(pk=cid, organization=active_org).exists():
            collection_pk = cid

    sk = _chat_session_key(request.user.id, str(collection_pk) if collection_pk is not None else None)
    history: list[dict] = request.session.get(sk, [])

    if request.method == "POST" and request.POST.get("action") == "clear":
        request.session.pop(sk, None)
        request.session.modified = True
        return redirect(_chat_redirect_url(collection_pk))

    question_form = QuestionForm(request.POST or None)
    if (
        request.method == "POST"
        and request.POST.get("action") != "clear"
        and question_form.is_valid()
    ):
        q = question_form.cleaned_data["question"].strip()
        if q:
            try:
                if not active_org:
                    raise RuntimeError("No organization membership found.")
                enforce_limit(active_org, "question", 1)
                answer, sources = rag.answer_question(
                    q,
                    user_id=request.user.id,
                    organization_id=active_org.id,
                    collection_id=collection_pk,
                )
                token_estimate = max(100, len((answer or "").split()) * 2)
                enforce_limit(active_org, "token", token_estimate)
                record_usage(active_org, request.user, "question", 1)
                record_usage(active_org, request.user, "token", token_estimate)
            except Exception as exc:
                messages.error(request, f"Assistant error: {exc}")
            else:
                history = history + [
                    {"role": "user", "content": q},
                    {"role": "assistant", "content": answer, "sources": sources},
                ]
                request.session[sk] = history[-20:]
                request.session.modified = True
                return redirect(_chat_redirect_url(collection_pk))

    active_collection = None
    if collection_pk is not None:
        active_collection = DocumentCollection.objects.filter(
            pk=collection_pk, organization=active_org
        ).first()

    return render(
        request,
        "rag_core/chat.html",
        {
            "question_form": question_form,
            "history": history,
            "active_collection": active_collection,
            "collection_pk": collection_pk,
        },
    )


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    active_org = _active_org_for_user(request.user)
    collections = DocumentCollection.objects.filter(organization=active_org).annotate(
        doc_count=Count("documents", distinct=True),
    )
    doc_count = IndexedDocument.objects.filter(organization=active_org).count()
    return render(
        request,
        "rag_core/dashboard.html",
        {
            "collections": collections,
            "doc_count": doc_count,
            "active_org": active_org,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def collection_create(request: HttpRequest) -> HttpResponse:
    active_org = _active_org_for_user(request.user)
    if not user_can_edit_workspace(request.user, active_org):
        messages.error(request, "You do not have permission to create workspaces.")
        return redirect("dashboard")
    if request.method == "POST":
        form = CollectionForm(request.POST)
        if form.is_valid():
            coll = DocumentCollection(
                user=request.user,
                organization=active_org,
                name=form.cleaned_data["name"].strip(),
                description=form.cleaned_data.get("description") or "",
            )
            coll.slug = ""
            coll.save()
            messages.success(
                request,
                f'Workspace "{coll.name}" is ready. Upload documents to index them.',
            )
            return redirect("collection_detail", pk=coll.pk)
    else:
        form = CollectionForm()
    return render(request, "rag_core/collection_create.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user_or_ip", rate="30/h", method=["POST"], block=True)
def collection_detail(request: HttpRequest, pk: int) -> HttpResponse:
    active_org = _active_org_for_user(request.user)
    coll = get_object_or_404(DocumentCollection, pk=pk, organization=active_org)
    documents = coll.documents.all()

    if request.method == "POST":
        if not user_can_edit_workspace(request.user, active_org):
            messages.error(request, "You do not have permission to upload documents.")
            return redirect("collection_detail", pk=coll.pk)
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            if not active_org:
                messages.error(request, "No active organization was found.")
                return redirect("collection_detail", pk=coll.pk)
            f = form.cleaned_data["file"]
            enforce_limit(active_org, "upload", 1)
            user_dir = settings.BASE_DIR / "documents" / "uploads" / str(request.user.id) / str(coll.pk)
            user_dir.mkdir(parents=True, exist_ok=True)
            dest = user_dir / f.name
            with open(dest, "wb") as out:
                for chunk in f.chunks():
                    out.write(chunk)
            try:
                existing = IndexedDocument.objects.filter(
                    organization=active_org,
                    collection=coll,
                    original_name=f.name,
                ).order_by("-uploaded_at").first()
                text = extract_text_from_path(dest, original_name=f.name)
                n, ids = rag.index_file_content(
                    text,
                    f.name,
                    user_id=request.user.id,
                    organization_id=active_org.id,
                    collection_id=coll.pk,
                    title=f.name,
                    previous_document_ids=(existing.search_document_ids if existing else None),
                )
                if existing:
                    existing.user = request.user
                    existing.stored_path = str(dest)
                    existing.chunk_count = n
                    existing.search_document_ids = ids
                    existing.save()
                else:
                    IndexedDocument.objects.create(
                        user=request.user,
                        organization=active_org,
                        collection=coll,
                        original_name=f.name,
                        stored_path=str(dest),
                        chunk_count=n,
                        search_document_ids=ids,
                    )
                messages.success(request, f"Indexed {n} chunk(s) from {f.name}.")
                record_usage(active_org, request.user, "upload", 1)
            except Exception as exc:
                messages.error(request, f"Indexing failed: {exc}")
            return redirect("collection_detail", pk=coll.pk)
    else:
        form = UploadForm()

    return render(
        request,
        "rag_core/collection_detail.html",
        {
            "collection": coll,
            "documents": documents,
            "upload_form": form,
        },
    )


@login_required
@require_POST
def document_delete(request: HttpRequest, pk: int, doc_pk: int) -> HttpResponse:
    active_org = _active_org_for_user(request.user)
    coll = get_object_or_404(DocumentCollection, pk=pk, organization=active_org)
    doc = get_object_or_404(
        IndexedDocument,
        pk=doc_pk,
        collection=coll,
        organization=active_org,
    )
    if not user_can_edit_workspace(request.user, active_org):
        messages.error(request, "You do not have permission to remove documents.")
        return redirect("collection_detail", pk=coll.pk)
    try:
        rag.remove_document_vectors(doc.search_document_ids or [])
    except Exception as exc:
        messages.error(request, f"Search delete warning: {exc}")
    try:
        from pathlib import Path

        Path(doc.stored_path).unlink(missing_ok=True)
    except OSError:
        pass
    name = doc.original_name
    doc.delete()
    messages.success(request, f"Removed {name} from this workspace.")
    return redirect("collection_detail", pk=coll.pk)


@login_required
@require_http_methods(["GET", "POST"])
def organization_settings(request: HttpRequest) -> HttpResponse:
    active_org = _active_org_for_user(request.user)
    if not active_org:
        messages.error(request, "No organization found for your account.")
        return redirect("dashboard")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "update_org" and user_can_manage_org(request.user, active_org):
            org_form = OrganizationForm(request.POST)
            member_form = OrganizationMemberForm()
            if org_form.is_valid():
                active_org.name = org_form.cleaned_data["name"].strip()
                active_org.plan = org_form.cleaned_data["plan"]
                active_org.slug = ""
                active_org.save()
                messages.success(request, "Organization settings updated.")
                return redirect("organization_settings")
        elif action == "add_member" and user_can_manage_org(request.user, active_org):
            member_form = OrganizationMemberForm(request.POST)
            org_form = OrganizationForm(initial={"name": active_org.name, "plan": active_org.plan})
            if member_form.is_valid():
                user = User.objects.filter(email__iexact=member_form.cleaned_data["email"]).first()
                if not user:
                    messages.error(request, "User not found by email. Ask them to register first.")
                else:
                    OrganizationMember.objects.update_or_create(
                        organization=active_org,
                        user=user,
                        defaults={"role": member_form.cleaned_data["role"]},
                    )
                    messages.success(request, f"{user.email} added to organization.")
                    return redirect("organization_settings")
        else:
            org_form = OrganizationForm(initial={"name": active_org.name, "plan": active_org.plan})
            member_form = OrganizationMemberForm()
    else:
        org_form = OrganizationForm(initial={"name": active_org.name, "plan": active_org.plan})
        member_form = OrganizationMemberForm()

    members = active_org.memberships.select_related("user").order_by("user__username")
    usage = (
        active_org.usage_events.values("metric")
        .annotate(total=Sum("amount"))
        .order_by("metric")
    )
    usage_map = {row["metric"]: row["total"] for row in usage}
    return render(
        request,
        "rag_core/organization_settings.html",
        {
            "active_org": active_org,
            "org_form": org_form,
            "member_form": member_form,
            "members": members,
            "can_manage_org": user_can_manage_org(request.user, active_org),
            "usage_map": usage_map,
        },
    )
