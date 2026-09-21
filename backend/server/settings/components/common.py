from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

SETTINGS_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = SETTINGS_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

load_dotenv(dotenv_path=BACKEND_DIR / ".env")
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = os.getenv("DEBUG", "True").lower() in {"1", "true", "yes"}

allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,.railway.app")
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts.split(",") if host.strip()]

railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
if railway_domain and railway_domain not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(railway_domain)

csrf_origins = os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:8000,https://*.up.railway.app",
)
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in csrf_origins.split(",") if origin.strip()
]
if railway_domain:
    CSRF_TRUSTED_ORIGINS.append(f"https://{railway_domain}")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.budget.apps.BudgetConfig",
    "rest_framework",
    "rest_framework_swagger",
    "drf_spectacular",
    "extra_checks",
    "corsheaders",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "server.urls"

cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in cors_origins.split(",") if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly"
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

FRONTEND_BUILD_DIR = Path(
    os.getenv("FRONTEND_BUILD_DIR", PROJECT_ROOT / "frontend" / "build")
)

SPECTACULAR_SETTINGS = {
    "TITLE": "Budget api",
    "DESCRIPTION": "api for Budget App",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            str(BACKEND_DIR / "templates"),
            str(FRONTEND_BUILD_DIR),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "server.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BACKEND_DIR / "staticfiles"
STATICFILES_DIRS = []
frontend_static = FRONTEND_BUILD_DIR / "static"
if frontend_static.exists():
    STATICFILES_DIRS.append(frontend_static)

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

if FRONTEND_BUILD_DIR.exists():
    WHITENOISE_ROOT = FRONTEND_BUILD_DIR

MEDIA_URL = "/media/"
MEDIA_ROOT = BACKEND_DIR / "media"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
