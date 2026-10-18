from django.contrib import admin

from .models import Contenedor, Servicio


@admin.register(Contenedor)
class ContenedorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "condicion", "estado", "precio", "stock", "activo")
    list_filter = ("tipo", "condicion", "estado", "activo")
    search_fields = ("nombre", "ubicacion")


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "precio", "unidad", "activo")
