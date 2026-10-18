from .mixins import es_personal


def tienda(request):
    """Datos globales para las plantillas: cantidad en el carrito y pedidos por atender."""
    user = request.user
    personal = es_personal(user)
    ctx = {"es_personal": personal, "carrito_cantidad": 0, "pedidos_pendientes": 0, "solicitudes_nuevas": 0}

    # Import diferido: evita ciclos al arrancar Django.
    from apps.cotizaciones.carrito import obtener_carrito
    from apps.cotizaciones.models import Cotizacion, Pedido

    carrito = obtener_carrito(request)
    if carrito is not None:
        ctx["carrito_cantidad"] = carrito.cantidad_total
    if personal:
        ctx["pedidos_pendientes"] = Pedido.objects.filter(estado=Pedido.Estado.PENDIENTE).count()
        ctx["solicitudes_nuevas"] = Cotizacion.objects.filter(estado=Cotizacion.Estado.SOLICITADA).count()
    return ctx
