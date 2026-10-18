from django.contrib import admin

from .models import Contenedor


@admin.register(Contenedor)
class ContenedorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "condicion", "estado", "precio", "stock", "activo")
    list_filter = ("tipo", "condicion", "estado", "activo")
    search_fields = ("nombre", "ubicacion")
