"""
Django settings for RAG portal (Azure OpenAI + Azure AI Search).
"""
import os
from pathlib import Path

from dotenv import load_dotenv
import dj_database_url
from config.keyvault import load_secret

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() in ("1", "true", "yes")

if not DEBUG and not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is false.")

_allowed = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
ALLOWED_HOSTS = [h.strip() for h in _allowed.split(",") if h.strip()]

_csrf_origins = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(",") if o.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rag_core",
]

if os.environ.get("OIDC_ENABLED", "false").lower() in ("1", "true", "yes"):
    INSTALLED_APPS.append("mozilla_django_oidc")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "rag_core.context_processors.app_shell",
                "rag_core.context_processors.feature_flags",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=int(os.environ.get("DB_CONN_MAX_AGE", "600")),
            ssl_require=not DEBUG,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Security baseline
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SECURE_SSL_REDIRECT", str(not DEBUG)).lower() in (
    "1",
    "true",
    "yes",
)
SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "31536000" if not DEBUG else "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
REFERRER_POLICY = "strict-origin-when-cross-origin"

SESSION_COOKIE_AGE = int(os.environ.get("SESSION_COOKIE_AGE", "28800"))
SESSION_SAVE_EVERY_REQUEST = True

# --- Azure RAG (read in services; documented in .env.example) ---
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "")

AZURE_SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT", "")
AZURE_SEARCH_KEY = os.environ.get("AZURE_SEARCH_KEY", "")
AZURE_SEARCH_INDEX_NAME = os.environ.get("AZURE_SEARCH_INDEX_NAME", "rag-documents")

# Must match your embedding model output size (1536 for ada-002 / text-embedding-3-small default)
EMBEDDING_DIMENSIONS = int(os.environ.get("EMBEDDING_DIMENSIONS", "1536"))

# Chunking
CHUNK_SIZE = int(os.environ.get("RAG_CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.environ.get("RAG_CHUNK_OVERLAP", "50"))
MAX_UPLOAD_MB = int(os.environ.get("RAG_MAX_UPLOAD_MB", "10"))
CHAT_RATE_LIMIT_PER_MIN = int(os.environ.get("CHAT_RATE_LIMIT_PER_MIN", "30"))
UPLOAD_RATE_LIMIT_PER_HOUR = int(os.environ.get("UPLOAD_RATE_LIMIT_PER_HOUR", "60"))
TIER_FREE_DAILY_QUESTIONS = int(os.environ.get("TIER_FREE_DAILY_QUESTIONS", "120"))
TIER_FREE_DAILY_UPLOADS = int(os.environ.get("TIER_FREE_DAILY_UPLOADS", "30"))
TIER_FREE_DAILY_TOKENS = int(os.environ.get("TIER_FREE_DAILY_TOKENS", "80000"))
TIER_PRO_DAILY_QUESTIONS = int(os.environ.get("TIER_PRO_DAILY_QUESTIONS", "1000"))
TIER_PRO_DAILY_UPLOADS = int(os.environ.get("TIER_PRO_DAILY_UPLOADS", "500"))
TIER_PRO_DAILY_TOKENS = int(os.environ.get("TIER_PRO_DAILY_TOKENS", "600000"))
DEFAULT_TENANT_PLAN = os.environ.get("DEFAULT_TENANT_PLAN", "free")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "rag-app-cache",
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        }
    },
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/app/"
LOGOUT_REDIRECT_URL = "/"

AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
if os.environ.get("OIDC_ENABLED", "false").lower() in ("1", "true", "yes"):
    AUTHENTICATION_BACKENDS = [
        "mozilla_django_oidc.auth.OIDCAuthenticationBackend",
        "django.contrib.auth.backends.ModelBackend",
    ]

OIDC_RP_CLIENT_ID = os.environ.get("OIDC_RP_CLIENT_ID", "")
OIDC_RP_CLIENT_SECRET = os.environ.get("OIDC_RP_CLIENT_SECRET", "")
OIDC_OP_AUTHORIZATION_ENDPOINT = os.environ.get("OIDC_OP_AUTHORIZATION_ENDPOINT", "")
OIDC_OP_TOKEN_ENDPOINT = os.environ.get("OIDC_OP_TOKEN_ENDPOINT", "")
OIDC_OP_USER_ENDPOINT = os.environ.get("OIDC_OP_USER_ENDPOINT", "")
OIDC_OP_JWKS_ENDPOINT = os.environ.get("OIDC_OP_JWKS_ENDPOINT", "")
OIDC_RP_SIGN_ALGO = os.environ.get("OIDC_RP_SIGN_ALGO", "RS256")

if os.environ.get("AZURE_KEYVAULT_URL"):
    vault_url = os.environ["AZURE_KEYVAULT_URL"]
    if not OIDC_RP_CLIENT_SECRET and os.environ.get("OIDC_RP_CLIENT_SECRET_NAME"):
        OIDC_RP_CLIENT_SECRET = load_secret(vault_url, os.environ["OIDC_RP_CLIENT_SECRET_NAME"])
    if not AZURE_OPENAI_API_KEY and os.environ.get("AZURE_OPENAI_API_KEY_SECRET_NAME"):
        AZURE_OPENAI_API_KEY = load_secret(vault_url, os.environ["AZURE_OPENAI_API_KEY_SECRET_NAME"])
    if not AZURE_SEARCH_KEY and os.environ.get("AZURE_SEARCH_KEY_SECRET_NAME"):
        AZURE_SEARCH_KEY = load_secret(vault_url, os.environ["AZURE_SEARCH_KEY_SECRET_NAME"])
