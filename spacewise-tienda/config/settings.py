import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

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
_CLAVE_DESARROLLO = "dev-only-insecure-key-cambiala-en-produccion"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", _CLAVE_DESARROLLO)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
if not DEBUG and SECRET_KEY in (_CLAVE_DESARROLLO, "cambia-esta-clave"):
    raise ImproperlyConfigured("Con DJANGO_DEBUG=0 debes definir una DJANGO_SECRET_KEY propia en .env.")
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]

# --- Despliegue con HTTPS (DJANGO_HTTPS=1 en el servidor) ---
HTTPS = os.environ.get("DJANGO_HTTPS", "0") == "1"
if HTTPS:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    # Los hostings atienden el HTTPS en un proxy y le pasan la petición a Django por HTTP.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SEGUNDOS", "3600"))
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
] or [f"https://{h}" for h in ALLOWED_HOSTS if HTTPS and "*" not in h and h not in ("localhost", "127.0.0.1")]
# Cantidad de proxies del hosting delante de Django: para conocer la IP real del visitante
# (límite de intentos de inicio de sesión). 0 = conexión directa.
PROXY_SALTOS = int(os.environ.get("DJANGO_PROXY_SALTOS", "0"))

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
    "whitenoise.middleware.WhiteNoiseMiddleware",  # sirve CSS/JS en producción
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

# Credenciales de MySQL en .env (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DB_NAME", "spacewise_db"),
        "USER": os.environ.get("DB_USER", "root"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "3306"),
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
STATIC_ROOT = BASE_DIR / "staticfiles"  # python manage.py collectstatic
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # En producción los archivos llevan una huella en el nombre para que el navegador no use versiones viejas.
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Imágenes subidas (fotos de contenedores). Si el hosting no sirve /media/ por su cuenta
# (PythonAnywhere sí puede), Django las sirve con DJANGO_SERVIR_MEDIA=1.
MEDIA_URL = "media/"
MEDIA_ROOT = Path(os.environ.get("DJANGO_MEDIA_ROOT", BASE_DIR / "media"))
SERVIR_MEDIA = DEBUG or os.environ.get("DJANGO_SERVIR_MEDIA", "1") == "1"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTHENTICATION_BACKENDS = ["apps.core.backends.CorreoOUsuarioBackend"]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "catalogo"
LOGOUT_REDIRECT_URL = "catalogo"

# --- Tienda / pedidos ---
# Correos del equipo interno que reciben aviso de cada pedido nuevo (separados por coma en .env).
PEDIDOS_NOTIFY_EMAILS = [e.strip() for e in os.environ.get("PEDIDOS_NOTIFY_EMAILS", "").split(",") if e.strip()]
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "SpaceWise <no-responder@spacewise.cl>")
# En desarrollo los correos se imprimen en la consola. Para enviarlos de verdad define en .env
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend y los EMAIL_HOST*.
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"

# --- Seguridad de cuentas ---
# La sesión se cierra tras estas horas sin actividad (cada visita renueva el plazo).
SESSION_COOKIE_AGE = int(os.environ.get("DJANGO_SESSION_HORAS", "8")) * 3600
SESSION_SAVE_EVERY_REQUEST = True
# Intentos fallidos de inicio de sesión antes de bloquear temporalmente (por cuenta e IP, y por IP).
LOGIN_MAX_INTENTOS = 5
LOGIN_MAX_INTENTOS_IP = 20
LOGIN_BLOQUEO_MINUTOS = 15
# Validez del enlace de «¿Olvidaste tu contraseña?».
PASSWORD_RESET_TIMEOUT = 2 * 3600

# Errores del servidor a la consola: en producción quedan en los logs del hosting.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"django": {"handlers": ["console"], "level": os.environ.get("DJANGO_LOG_LEVEL", "WARNING")}},
}
