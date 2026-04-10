from __future__ import annotations

from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from .forms import CollectionForm, QuestionForm, SignUpForm, UploadForm
from .models import DocumentCollection, IndexedDocument
from .services import rag
from .services.text_extract import extract_text_from_path


def health(_request: HttpRequest) -> HttpResponse:
    return HttpResponse("ok", content_type="text/plain")


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


@require_http_methods(["GET", "POST"])
def register(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user: User = form.save()
            login(request, user)
            DocumentCollection.objects.create(
                user=user,
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
def chat(request: HttpRequest) -> HttpResponse:
    collection_pk: int | None = None
    raw = (request.GET.get("collection") or request.POST.get("collection") or "").strip()
    if raw.isdigit():
        cid = int(raw)
        if DocumentCollection.objects.filter(pk=cid, user=request.user).exists():
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
                answer, sources = rag.answer_question(
                    q,
                    user_id=request.user.id,
                    collection_id=collection_pk,
                )
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
            pk=collection_pk, user=request.user
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
    collections = DocumentCollection.objects.filter(user=request.user).annotate(
        doc_count=Count("documents", distinct=True),
    )
    doc_count = IndexedDocument.objects.filter(user=request.user).count()
    return render(
        request,
        "rag_core/dashboard.html",
        {
            "collections": collections,
            "doc_count": doc_count,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def collection_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = CollectionForm(request.POST)
        if form.is_valid():
            coll = DocumentCollection(
                user=request.user,
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
def collection_detail(request: HttpRequest, pk: int) -> HttpResponse:
    coll = get_object_or_404(DocumentCollection, pk=pk, user=request.user)
    documents = coll.documents.all()

    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data["file"]
            user_dir = settings.BASE_DIR / "documents" / "uploads" / str(request.user.id) / str(coll.pk)
            user_dir.mkdir(parents=True, exist_ok=True)
            dest = user_dir / f.name
            with open(dest, "wb") as out:
                for chunk in f.chunks():
                    out.write(chunk)
            try:
                text = extract_text_from_path(dest, original_name=f.name)
                n, ids = rag.index_file_content(
                    text,
                    f.name,
                    user_id=request.user.id,
                    collection_id=coll.pk,
                    title=f.name,
                )
                IndexedDocument.objects.create(
                    user=request.user,
                    collection=coll,
                    original_name=f.name,
                    stored_path=str(dest),
                    chunk_count=n,
                    search_document_ids=ids,
                )
                messages.success(request, f"Indexed {n} chunk(s) from {f.name}.")
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
    coll = get_object_or_404(DocumentCollection, pk=pk, user=request.user)
    doc = get_object_or_404(IndexedDocument, pk=doc_pk, collection=coll, user=request.user)
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
