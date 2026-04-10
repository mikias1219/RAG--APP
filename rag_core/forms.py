from django import forms


class QuestionForm(forms.Form):
    question = forms.CharField(
        label="Your question",
        max_length=2000,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "form-control",
                "placeholder": "Ask something about your indexed documents…",
            }
        ),
    )


class UploadForm(forms.Form):
    file = forms.FileField(
        label="Text or Markdown file",
        help_text="Upload .txt or .md (max size set by RAG_MAX_UPLOAD_MB).",
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        from django.conf import settings

        max_bytes = settings.RAG_MAX_UPLOAD_MB * 1024 * 1024
        if f.size > max_bytes:
            raise forms.ValidationError("File too large.")
        name = f.name.lower()
        if not (name.endswith(".txt") or name.endswith(".md")):
            raise forms.ValidationError("Only .txt and .md files are allowed.")
        return f
