from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import QuestionForm, UploadForm
from .models import IndexedDocument
from .services import rag


def health(_request: HttpRequest) -> HttpResponse:
    return HttpResponse("ok", content_type="text/plain")


def home(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "rag_core/home.html",
        {
            "has_azure": bool(
                settings.AZURE_OPENAI_ENDPOINT
                and settings.AZURE_SEARCH_ENDPOINT
            ),
        },
    )


@require_http_methods(["GET", "POST"])
def chat(request: HttpRequest) -> HttpResponse:
    answer = ""
    sources: list[dict] = []
    form = QuestionForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            answer, sources = rag.answer_question(form.cleaned_data["question"])
        except Exception as exc:
            messages.error(request, f"RAG error: {exc}")

    return render(
        request,
        "rag_core/chat.html",
        {"form": form, "answer": answer, "sources": sources},
    )


@require_http_methods(["GET", "POST"])
def upload(request: HttpRequest) -> HttpResponse:
    form = UploadForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        f = form.cleaned_data["file"]
        upload_dir = settings.BASE_DIR / "documents" / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        dest = upload_dir / f.name
        with open(dest, "wb") as out:
            for chunk in f.chunks():
                out.write(chunk)
        try:
            text = dest.read_text(encoding="utf-8", errors="replace")
            n = rag.index_file_content(text, source_name=f.name, title=f.name)
            IndexedDocument.objects.create(original_name=f.name, stored_path=str(dest))
            messages.success(request, f"Indexed {n} chunk(s) from {f.name}.")
        except Exception as exc:
            messages.error(request, f"Indexing failed: {exc}")
        return redirect("upload")

    return render(request, "rag_core/upload.html", {"form": form})
