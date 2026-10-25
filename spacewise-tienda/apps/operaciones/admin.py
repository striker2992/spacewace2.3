from django.contrib import admin

from .models import DetalleGarantia, Garantia


class DetalleGarantiaInline(admin.TabularInline):
    model = DetalleGarantia
    extra = 0


@admin.register(Garantia)
class GarantiaAdmin(admin.ModelAdmin):
    list_display = ("numero", "pedido", "estado", "fecha_solicitud", "resuelta_por")
    list_filter = ("estado", "fecha_solicitud")
    search_fields = ("pedido__numero_pedido", "pedido__cliente__nombre", "pedido__cliente__rut")
    readonly_fields = ("fecha_solicitud", "fecha_resolucion")
    inlines = [DetalleGarantiaInline]
