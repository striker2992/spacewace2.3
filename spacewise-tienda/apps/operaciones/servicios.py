"""Reglas de negocio de garantías: solicitar (cliente) y resolver (equipo interno)."""

from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.cotizaciones.models import Pedido

from .models import DetalleGarantia, Garantia


class GarantiaError(Exception):
    """Error de negocio mostrable al usuario."""


def solicitar_garantia(pedido, motivo, cantidades):
    """Crea la garantía de un pedido entregado. `cantidades`: [(ItemPedido, n), ...] con n > 0."""
    with transaction.atomic():
        # Se relee bloqueado para que un doble clic no cree dos solicitudes.
        pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
        if not pedido.admite_garantia:
            raise GarantiaError(pedido.motivo_sin_garantia)
        lineas = [(item, n) for item, n in cantidades if n]
        if not lineas:
            raise GarantiaError("Indica al menos un contenedor afectado.")
        for item, n in lineas:
            if item.pedido_id != pedido.pk or n > item.cantidad:
                raise GarantiaError(f"«{item.contenedor.nombre}»: compraste {item.cantidad}.")
        garantia = Garantia.objects.create(pedido=pedido, motivo=motivo)
        DetalleGarantia.objects.bulk_create(
            DetalleGarantia(garantia=garantia, contenedor_id=item.contenedor_id, cantidad=n) for item, n in lineas
        )
    return garantia


def resolver_garantia(garantia, estado, resolucion, usuario):
    """El ejecutivo aprueba o rechaza una garantía pendiente y deja la resolución para el cliente."""
    nuevo = Garantia.Estado(estado)
    if nuevo == Garantia.Estado.PENDIENTE:
        raise GarantiaError("Elige aprobar o rechazar.")
    with transaction.atomic():
        actual = Garantia.objects.select_for_update().get(pk=garantia.pk)
        if actual.estado != Garantia.Estado.PENDIENTE:
            raise GarantiaError(f"{actual.numero} ya fue {actual.get_estado_display().lower()}.")
        actual.estado = nuevo
        actual.resolucion = resolucion
        actual.resuelta_por = usuario
        actual.fecha_resolucion = timezone.now()
        actual.save()
    notificar_resolucion(actual)
    return actual


def notificar_resolucion(garantia):
    cliente = garantia.pedido.cliente
    email = cliente.email or (cliente.usuario.email if cliente.usuario else "")
    if not email:
        return
    send_mail(
        subject=f"Tu garantía {garantia.numero} fue {garantia.get_estado_display().lower()}",
        message=(
            f"Hola {cliente.nombre},\n\nRevisamos tu solicitud de garantía {garantia.numero} "
            f"del pedido {garantia.pedido.numero_pedido}.\n\nResultado: {garantia.get_estado_display()}\n"
            f"{garantia.resolucion}\n\nSpaceWise"
        ),
        from_email=None,
        recipient_list=[email],
        fail_silently=True,
    )
