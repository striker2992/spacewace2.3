"""Settings override for running with SQLite (screenshots/demo)."""
from config.settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_demo.sqlite3",
    }
}
