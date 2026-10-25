"""Reglas de negocio de pedidos: confirmar compra, cambiar estado y avisar por correo."""

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F

from apps.contenedores.models import Contenedor

from .models import Cotizacion, ItemPedido, Pedido, ServicioPedido


class PedidoError(Exception):
    """Error de negocio mostrable al usuario."""


# ---------------------------------------------------------------------------
# Confirmar compra
# ---------------------------------------------------------------------------
def crear_pedido(carrito, cliente, datos):
    """Convierte el carrito en un Pedido (+ ItemPedido) y descuenta el stock.

    Todo ocurre en una transacción: los contenedores se bloquean, se revalida el stock
    (otro cliente pudo comprar mientras tanto) y los precios se copian del catálogo.
    `datos`: direccion_entrega, telefono_contacto, metodo_contacto, notas.
    """
    _validar_comprador(cliente)
    with transaction.atomic():
        items = list(carrito.items.select_related("contenedor"))
        if not items:
            raise PedidoError("Tu carrito está vacío.")
        bloqueados = _bloquear_stock(items)
        pedido = _nuevo_pedido(cliente, datos)
        total = 0
        for item in items:
            c = bloqueados[item.contenedor_id]
            ItemPedido.objects.create(
                pedido=pedido, contenedor=c, cantidad=item.cantidad, precio_unitario=c.precio
            )
            total += item.cantidad * c.precio
            Contenedor.objects.filter(pk=c.pk).update(stock=F("stock") - item.cantidad)
        pedido.total = total
        pedido.save(update_fields=["total"])
        carrito.items.all().delete()

    notificar_pedido_nuevo(pedido)
    return pedido


def comprar_cotizacion(cotizacion, cliente, datos):
    """RQ06: convierte una cotización aprobada en un Pedido con los precios valorizados.

    A diferencia del carrito, los precios NO se toman del catálogo sino de la cotización
    (lo que el ejecutivo aprobó). Una cotización se compra una sola vez; si su pedido se
    cancela, se puede volver a comprar.
    """
    _validar_comprador(cliente)
    with transaction.atomic():
        # Se relee bloqueada para que un doble clic no genere dos pedidos.
        cot = Cotizacion.objects.select_for_update().get(pk=cotizacion.pk)
        if cot.cliente_id != cliente.pk:
            raise PedidoError("Esta cotización no es tuya.")
        if cot.estado != Cotizacion.Estado.APROBADA:
            raise PedidoError("Solo se pueden comprar cotizaciones aprobadas.")
        if cot.pedido_vigente:
            raise PedidoError(f"Esta cotización ya se compró en el pedido {cot.pedido_vigente.numero_pedido}.")
        items = list(cot.items.all())
        servicios = list(cot.servicios.all())
        if not items:
            raise PedidoError("La cotización no tiene contenedores.")
        bloqueados = _bloquear_stock(items)

        pedido = _nuevo_pedido(cliente, datos, cotizacion=cot)
        for item in items:
            ItemPedido.objects.create(
                pedido=pedido, contenedor_id=item.contenedor_id, cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
            )
            Contenedor.objects.filter(pk=bloqueados[item.contenedor_id].pk).update(
                stock=F("stock") - item.cantidad
            )
        for s in servicios:
            ServicioPedido.objects.create(
                pedido=pedido, servicio_id=s.servicio_id, cantidad=s.cantidad, precio_unitario=s.precio_unitario
            )
        pedido.total = sum(i.subtotal for i in items) + sum(s.subtotal for s in servicios)
        pedido.save(update_fields=["total"])

    notificar_pedido_nuevo(pedido)
    return pedido


def _validar_comprador(cliente):
    from apps.core.mixins import es_personal  # import diferido: evita ciclos

    if cliente.usuario_id and es_personal(cliente.usuario):
        raise PedidoError("Las cuentas del equipo interno no pueden realizar compras.")


def _bloquear_stock(lineas):
    """Bloquea los contenedores de `lineas` (con contenedor_id y cantidad) y revalida su stock.

    Otro cliente pudo comprar mientras tanto, así que se revisa dentro de la transacción.
    """
    bloqueados = {
        c.pk: c
        for c in Contenedor.objects.select_for_update().filter(pk__in=[l.contenedor_id for l in lineas])
    }
    problemas = []
    for linea in lineas:
        c = bloqueados[linea.contenedor_id]
        vendible = c.activo and c.estado == Contenedor.Estado.DISPONIBLE
        if not vendible or c.stock < linea.cantidad:
            problemas.append(
                f"«{c.nombre}»: pediste {linea.cantidad} y hay {c.stock if vendible else 0} disponible(s)."
            )
    if problemas:
        raise PedidoError("Cambió la disponibilidad de algunos contenedores. " + " ".join(problemas))
    return bloqueados


def _nuevo_pedido(cliente, datos, cotizacion=None):
    return Pedido.objects.create(
        cliente=cliente,
        cotizacion=cotizacion,
        direccion_entrega=datos["direccion_entrega"],
        telefono_contacto=datos["telefono_contacto"],
        metodo_contacto=datos["metodo_contacto"],
        notas=datos.get("notas", ""),
    )


# ---------------------------------------------------------------------------
# Cambiar estado (panel interno y Django Admin pasan por aquí)
# ---------------------------------------------------------------------------
def cambiar_estado_pedido(pedido, nuevo_estado):
    """Aplica una transición válida. Al cancelar, el stock vuelve al inventario."""
    nuevo = Pedido.Estado(nuevo_estado)
    with transaction.atomic():
        # Se relee bloqueado para no cancelar dos veces (doble clic / dos vendedores).
        actual = Pedido.objects.select_for_update().get(pk=pedido.pk)
        if nuevo not in Pedido.TRANSICIONES[Pedido.Estado(actual.estado)]:
            raise PedidoError(
                f"No se puede pasar un pedido de «{actual.get_estado_display()}» a «{nuevo.label}»."
            )
        if nuevo == Pedido.Estado.CANCELADO:
            for item in actual.items.all():
                Contenedor.objects.filter(pk=item.contenedor_id).update(
                    stock=F("stock") + item.cantidad
                )
        actual.estado = nuevo
        actual.save(update_fields=["estado", "fecha_actualizacion"])
    pedido.estado = actual.estado
    notificar_cambio_estado(pedido)
    return pedido


# ---------------------------------------------------------------------------
# Notificaciones por correo (consola en desarrollo; ver EMAIL_BACKEND en settings)
# ---------------------------------------------------------------------------
def notificar_pedido_nuevo(pedido):
    destinatarios = settings.PEDIDOS_NOTIFY_EMAILS
    if not destinatarios:
        return
    send_mail(
        subject=f"Nuevo pedido {pedido.numero_pedido}",
        message=(
            f"Cliente: {pedido.cliente}\nTotal: ${pedido.total:,.0f}\n"
            f"Contacto preferido: {pedido.get_metodo_contacto_display()} ({pedido.telefono_contacto})\n"
            f"Entrega: {pedido.direccion_entrega}"
        ),
        from_email=None,
        recipient_list=destinatarios,
        fail_silently=True,
    )


def notificar_cambio_estado(pedido):
    email = pedido.cliente.email or (pedido.cliente.usuario.email if pedido.cliente.usuario else "")
    if not email:
        return
    send_mail(
        subject=f"Tu pedido {pedido.numero_pedido} está {pedido.get_estado_display().lower()}",
        message=(
            f"Hola {pedido.cliente.nombre},\n\nTu pedido {pedido.numero_pedido} "
            f"cambió a: {pedido.get_estado_display()}.\n\nGracias por comprar en SpaceWise."
        ),
        from_email=None,
        recipient_list=[email],
        fail_silently=True,
    )
