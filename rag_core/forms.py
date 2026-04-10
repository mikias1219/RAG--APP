from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from rag_core.services.text_extract import allowed_upload_suffixes


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Used for account recovery and notifications.")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if hasattr(field.widget, "attrs"):
                field.widget.attrs.setdefault("class", "inp")


class CollectionForm(forms.Form):
    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "inp", "placeholder": "e.g. Q4 Contracts"}),
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "inp",
                "rows": 2,
                "placeholder": "Optional description for your team",
            }
        ),
    )


class QuestionForm(forms.Form):
    question = forms.CharField(
        label="",
        max_length=4000,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "class": "chat-input",
                "placeholder": "Ask a question about your documents…",
                "autocomplete": "off",
            }
        ),
    )


class UploadForm(forms.Form):
    file = forms.FileField(
        label="",
        widget=forms.ClearableFileInput(attrs={"class": "inp-file"}),
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        from django.conf import settings

        max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
        if f.size > max_bytes:
            raise forms.ValidationError("File too large.")
        name = f.name.lower()
        suffix = ""
        if "." in name:
            suffix = "." + name.rsplit(".", 1)[-1]
        if suffix not in allowed_upload_suffixes():
            raise forms.ValidationError("Allowed types: .txt, .md, .pdf, .docx.")
        return f
