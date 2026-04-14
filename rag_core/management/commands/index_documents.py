"""
Index files into Azure AI Search for a specific user collection (CLI).

Uploads in the web app index automatically. This command is for admins/scripts.

Usage:
  python manage.py index_documents --username alice --collection-id 1 --path ./file.pdf
  python manage.py index_documents --username alice --collection-id 1 \\
      --folder documents/sample
"""

from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from rag_core.services import rag
from rag_core.services.text_extract import extract_text_from_path


class Command(BaseCommand):
    help = "Index documents into a user's collection (requires --username and --collection-id)."

    def add_arguments(self, parser):
        parser.add_argument("--username", type=str, required=True)
        parser.add_argument("--collection-id", type=int, required=True)
        parser.add_argument("--path", type=str, default="", help="Single file to index.")
        parser.add_argument(
            "--folder",
            type=str,
            default="",
            help="Folder of .txt, .md, .pdf, .docx to index.",
        )

    def handle(self, *args, **options):
        username = options["username"]
        coll_id = options["collection_id"]
        path_arg = options.get("path") or ""
        folder_arg = options.get("folder") or ""

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stderr.write(f"User not found: {username}")
            return

        from rag_core.models import DocumentCollection

        try:
            coll = DocumentCollection.objects.get(pk=coll_id, user=user)
        except DocumentCollection.DoesNotExist:
            self.stderr.write(f"Collection {coll_id} not found for user {username}.")
            return

        files: list[Path] = []
        if path_arg:
            p = Path(path_arg)
            if not p.is_file():
                self.stderr.write(f"Not a file: {p}")
                return
            files.append(p)
        elif folder_arg:
            folder = Path(folder_arg)
            if not folder.is_dir():
                self.stderr.write(f"Not a folder: {folder}")
                return
            for ext in ("*.txt", "*.md", "*.pdf", "*.docx"):
                files.extend(folder.glob(ext))
        else:
            self.stderr.write(
                "Provide --path FILE or --folder DIR. Example:\n"
                "  python manage.py index_documents --username you --collection-id 1 "
                "--path documents/sample/welcome.md"
            )
            return

        if not files:
            self.stdout.write("No matching files.")
            return

        total = 0
        for path in sorted(set(files)):
            text = extract_text_from_path(path)
            n, _ids = rag.index_file_content(
                text,
                path.name,
                user_id=user.id,
                organization_id=coll.organization_id or 0,
                collection_id=coll.pk,
                title=path.name,
            )
            total += n
            self.stdout.write(f"Indexed {path}: {n} chunks")

        self.stdout.write(self.style.SUCCESS(f"Done. Total chunks: {total}"))
