"""Reglas de negocio de pedidos: confirmar compra, cambiar estado y avisar por correo."""

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F

from apps.contenedores.models import Contenedor

from .models import ItemPedido, Pedido


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
    from apps.core.mixins import es_personal  # import diferido: evita ciclos

    if cliente.usuario_id and es_personal(cliente.usuario):
        raise PedidoError("Las cuentas del equipo interno no pueden realizar compras.")
    with transaction.atomic():
        items = list(carrito.items.select_related("contenedor"))
        if not items:
            raise PedidoError("Tu carrito está vacío.")

        bloqueados = {
            c.pk: c
            for c in Contenedor.objects.select_for_update().filter(
                pk__in=[i.contenedor_id for i in items]
            )
        }
        problemas = []
        for item in items:
            c = bloqueados[item.contenedor_id]
            vendible = c.activo and c.estado == Contenedor.Estado.DISPONIBLE
            if not vendible or c.stock < item.cantidad:
                problemas.append(
                    f"«{c.nombre}»: pediste {item.cantidad} y hay {c.stock if vendible else 0} disponible(s)."
                )
        if problemas:
            raise PedidoError("Cambió la disponibilidad de algunos contenedores. " + " ".join(problemas))

        pedido = Pedido.objects.create(
            cliente=cliente,
            direccion_entrega=datos["direccion_entrega"],
            telefono_contacto=datos["telefono_contacto"],
            metodo_contacto=datos["metodo_contacto"],
            notas=datos.get("notas", ""),
        )
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
