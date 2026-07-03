"""
Django settings for the AI-Driven Student Performance Analytics backend.

This is a course-project-oriented configuration: SQLite for quick start,
with a commented PostgreSQL block for when you switch to the real DB.
"""
from pathlib import Path

# ml-service/   (manage.py lives here)
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Security (dev defaults; do NOT use this key in production) -------------
SECRET_KEY = "dev-insecure-change-me-before-deployment"
DEBUG = True
ALLOWED_HOSTS = ["*"]

# --- Applications -----------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    # Local
    "analytics",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # must come before CommonMiddleware
    "django.middleware.security.SecurityMiddleware",
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
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database ---------------------------------------------------------------
# Quick start: SQLite. Switch to PostgreSQL when ready (see commented block).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": "student_analytics",
#         "USER": "postgres",
#         "PASSWORD": "postgres",
#         "HOST": "localhost",
#         "PORT": "5432",
#     }
# }

# --- Password validation ----------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- I18N -------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- Static files -----------------------------------------------------------
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Django REST Framework --------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

# --- CORS (allow the React dev server to call the API) ----------------------
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",  # Vite default
]

# --- Machine Learning model artifacts ---------------------------------------
# Trained models (.pkl) produced by analytics/ml/train.py live here.
ML_MODELS_DIR = BASE_DIR / "ml_models"
