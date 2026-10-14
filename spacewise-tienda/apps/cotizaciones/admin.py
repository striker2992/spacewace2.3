from django.contrib import admin, messages

from .models import Carrito, Cotizacion, CotizacionItem, ItemCarrito, ItemPedido, Pedido
from .servicios import PedidoError, cambiar_estado_pedido


class ItemInline(admin.TabularInline):
    model = CotizacionItem
    extra = 0


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ("numero", "cliente", "estado", "fecha")
    list_filter = ("estado",)
    inlines = [ItemInline]


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    can_delete = False
    readonly_fields = ("contenedor", "cantidad", "precio_unitario", "subtotal")
    fields = ("contenedor", "cantidad", "precio_unitario", "subtotal")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("numero_pedido", "cliente", "estado", "total", "fecha_creacion")
    list_filter = ("estado", "fecha_creacion")
    date_hierarchy = "fecha_creacion"
    search_fields = ("numero_pedido", "cliente__nombre", "cliente__rut", "cliente__email")
    readonly_fields = ("numero_pedido", "cliente", "total", "fecha_creacion", "fecha_actualizacion")
    inlines = [ItemPedidoInline]
    actions = ["marcar_en_proceso", "marcar_despachado", "marcar_completado", "marcar_cancelado"]

    def save_model(self, request, obj, form, change):
        # Un cambio de estado desde el formulario pasa por el servicio para respetar las
        # transiciones válidas y devolver el stock al cancelar.
        if change and "estado" in form.changed_data:
            nuevo = obj.estado
            obj.estado = form.initial["estado"]
            super().save_model(request, obj, form, change)
            self._cambiar(request, obj, nuevo)
        else:
            super().save_model(request, obj, form, change)

    def _cambiar(self, request, pedido, nuevo):
        try:
            cambiar_estado_pedido(pedido, nuevo)
            return True
        except PedidoError as e:
            self.message_user(request, f"{pedido.numero_pedido}: {e}", level=messages.ERROR)
            return False

    def _accion(self, request, queryset, nuevo):
        ok = sum(self._cambiar(request, p, nuevo) for p in queryset)
        if ok:
            self.message_user(request, f"{ok} pedido(s) actualizados.", level=messages.SUCCESS)

    @admin.action(description="Marcar como En proceso")
    def marcar_en_proceso(self, request, queryset):
        self._accion(request, queryset, Pedido.Estado.EN_PROCESO)

    @admin.action(description="Marcar como Despachado")
    def marcar_despachado(self, request, queryset):
        self._accion(request, queryset, Pedido.Estado.DESPACHADO)

    @admin.action(description="Marcar como Completado")
    def marcar_completado(self, request, queryset):
        self._accion(request, queryset, Pedido.Estado.COMPLETADO)

    @admin.action(description="Cancelar (devuelve el stock)")
    def marcar_cancelado(self, request, queryset):
        self._accion(request, queryset, Pedido.Estado.CANCELADO)


class ItemCarritoInline(admin.TabularInline):
    model = ItemCarrito
    extra = 0


@admin.register(Carrito)
class CarritoAdmin(admin.ModelAdmin):
    list_display = ("__str__", "usuario", "actualizado")
    inlines = [ItemCarritoInline]
