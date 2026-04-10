"""
Index .txt / .md files from documents/sample and documents/uploads.

Usage:
  python manage.py index_documents
  python manage.py index_documents --path path/to/file.md
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from rag_core.services import rag


class Command(BaseCommand):
    help = "Chunk, embed, and upload local documents to Azure AI Search."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            default="",
            help="Single file to index; default: scan sample + uploads folders.",
        )

    def handle(self, *args, **options):
        base = Path(settings.BASE_DIR)
        single = options.get("path") or ""
        files: list[Path] = []

        if single:
            p = Path(single)
            if not p.is_file():
                self.stderr.write(f"Not a file: {p}")
                return
            files.append(p)
        else:
            for folder in (base / "documents" / "sample", base / "documents" / "uploads"):
                if folder.is_dir():
                    for ext in ("*.txt", "*.md"):
                        files.extend(folder.glob(ext))

        if not files:
            self.stdout.write("No files found. Add .txt/.md under documents/sample or documents/uploads.")
            return

        total_chunks = 0
        for path in sorted(set(files)):
            text = path.read_text(encoding="utf-8", errors="replace")
            source_name = path.name
            n = rag.index_file_content(text, source_name=source_name, title=source_name)
            total_chunks += n
            self.stdout.write(f"Indexed {path}: {n} chunks")

        self.stdout.write(self.style.SUCCESS(f"Done. Total chunks uploaded: {total_chunks}"))
