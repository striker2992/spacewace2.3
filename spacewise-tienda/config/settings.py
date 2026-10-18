import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _cargar_dotenv(ruta):
    """Lee KEY=VALUE de un archivo .env (sin dependencias extra). No pisa variables ya definidas."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        os.environ.setdefault(clave.strip(), valor.strip().strip("\"'"))


_cargar_dotenv(BASE_DIR / ".env")

# DESARROLLO por defecto. En producción define DJANGO_SECRET_KEY, DJANGO_DEBUG=0 y DJANGO_ALLOWED_HOSTS.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-cambiala-en-produccion")
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
    "apps.clientes",
    "apps.contenedores",
    "apps.cotizaciones",
    "apps.operaciones",
    "apps.vendedores",
]

MIDDLEWARE = [
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
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.tienda",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "spacewise_db",  # Nombre de la BD creada en el Paso 1
        "USER": "root",  # Tu usuario de MySQL
        "PASSWORD": "pato2005",  # Tu contraseña de MySQL
        "HOST": "127.0.0.1",  # Servidor local
        "PORT": "3306",  # Puerto por defecto de MySQL
        "OPTIONS": {
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Imágenes subidas (fotos de contenedores). En producción sírvelas con el servidor web.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTHENTICATION_BACKENDS = ["apps.core.backends.CorreoOUsuarioBackend"]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "catalogo"
LOGOUT_REDIRECT_URL = "catalogo"

# --- Tienda / pedidos ---
# Correos del equipo interno que reciben aviso de cada pedido nuevo (separados por coma en .env).
PEDIDOS_NOTIFY_EMAILS = [e.strip() for e in os.environ.get("PEDIDOS_NOTIFY_EMAILS", "").split(",") if e.strip()]
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "SpaceWise <no-responder@spacewise.cl>")
# En desarrollo los correos se imprimen en la consola. En producción define EMAIL_BACKEND/EMAIL_HOST en .env.
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
