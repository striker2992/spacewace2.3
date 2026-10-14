from django.apps import AppConfig


class CotizacionesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cotizaciones"

    def ready(self):
        from . import signals  # noqa: F401  (registra la fusión de carritos al iniciar sesión)
