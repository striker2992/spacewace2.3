"""Lógica del carrito: un carrito por usuario autenticado, o uno anónimo ligado a la sesión."""

from django.db import transaction

from apps.contenedores.models import Contenedor

from .models import Carrito, ItemCarrito

SESSION_KEY = "carrito_id"
CANTIDAD_MAXIMA = 99


class CarritoError(Exception):
    """Error de negocio mostrable al usuario (sin stock, contenedor inactivo, etc.)."""


def obtener_carrito(request, crear=False):
    """Devuelve el carrito del request. Con crear=False puede devolver None."""
    if request.user.is_authenticated:
        if crear:
            carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
            return carrito
        return Carrito.objects.filter(usuario=request.user).first()

    carrito_id = request.session.get(SESSION_KEY)
    carrito = (
        Carrito.objects.filter(pk=carrito_id, usuario__isnull=True).first() if carrito_id else None
    )
    if carrito is None and crear:
        carrito = Carrito.objects.create()
        request.session[SESSION_KEY] = carrito.pk
    return carrito


def _limite(contenedor):
    return min(contenedor.stock, CANTIDAD_MAXIMA)


def agregar_item(carrito, contenedor, cantidad=1):
    """Suma `cantidad` al ítem (lo crea si no existe) sin superar el stock."""
    if not contenedor.activo:
        raise CarritoError("Este contenedor ya no está disponible.")
    if contenedor.stock <= 0:
        raise CarritoError("Este contenedor está sin stock.")
    aviso = None
    with transaction.atomic():
        item, _ = ItemCarrito.objects.select_for_update().get_or_create(
            carrito=carrito, contenedor=contenedor, defaults={"cantidad": 0}
        )
        nueva = item.cantidad + cantidad
        limite = _limite(contenedor)
        if nueva > limite:
            nueva = limite
            aviso = (
                f"Solo hay {contenedor.stock} unidad(es) de «{contenedor.nombre}»; "
                f"dejamos {limite} en tu carrito."
            )
        item.cantidad = nueva
        item.save(update_fields=["cantidad"])
    if aviso:  # se lanza fuera del atomic para que el guardado no se revierta
        raise CarritoError(aviso)
    return item


def actualizar_item(item, cantidad):
    """Fija la cantidad. 0 (o menos) elimina el ítem. Se limita al stock disponible."""
    if cantidad <= 0:
        item.delete()
        return None
    limite = _limite(item.contenedor)
    if limite <= 0:
        item.delete()
        raise CarritoError(f"«{item.contenedor.nombre}» se quedó sin stock y lo quitamos del carrito.")
    if cantidad > limite:
        item.cantidad = limite
        item.save(update_fields=["cantidad"])
        raise CarritoError(f"Solo hay {limite} unidad(es) de «{item.contenedor.nombre}».")
    item.cantidad = cantidad
    item.save(update_fields=["cantidad"])
    return item


def fusionar_carritos(request, user):
    """Al iniciar sesión: pasa los ítems del carrito anónimo (sesión) al carrito del usuario."""
    carrito_id = request.session.pop(SESSION_KEY, None)
    if not carrito_id:
        return
    anonimo = Carrito.objects.filter(pk=carrito_id, usuario__isnull=True).first()
    if anonimo is None:
        return
    with transaction.atomic():
        destino, _ = Carrito.objects.get_or_create(usuario=user)
        for item in anonimo.items.select_related("contenedor"):
            try:
                agregar_item(destino, item.contenedor, item.cantidad)
            except CarritoError:
                # Sin stock o con tope: se conserva lo que cupo y se sigue con el resto.
                pass
        anonimo.delete()
