from django.contrib import admin

from .models import SeguridadCuenta


@admin.register(SeguridadCuenta)
class SeguridadCuentaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "intentos_fallidos", "bloqueada_en", "ultima_ip", "desbloqueada_en", "desbloqueada_por")
    list_filter = (("bloqueada_en", admin.EmptyFieldListFilter),)
    search_fields = ("usuario__username", "usuario__email")
    readonly_fields = ("ultima_ip", "desbloqueada_en", "desbloqueada_por")
