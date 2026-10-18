"""Vistas para el cliente final: carrito, checkout y sus pedidos."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.clientes.models import Cliente
from apps.contenedores.models import Contenedor
from apps.core.mixins import SoloClientesMixin, solo_clientes

from .carrito import CANTIDAD_MAXIMA, CarritoError, actualizar_item, agregar_item, obtener_carrito
from .forms import CheckoutForm
from .models import ItemCarrito, Pedido
from .servicios import PedidoError, crear_pedido


def _entero(valor, defecto=1):
    try:
        return max(0, min(int(valor), CANTIDAD_MAXIMA))
    except (TypeError, ValueError):
        return defecto


def _volver(request, defecto="tienda:carrito"):
    """Redirige a `next` si es una URL interna segura; si no, al destino por defecto."""
    destino = request.POST.get("next", "")
    if destino and url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(destino)
    return redirect(defecto)


# ---------------------------------------------------------------------------
# B. Carrito (funciona sin iniciar sesión)
# ---------------------------------------------------------------------------
class CarritoView(SoloClientesMixin, TemplateView):
    template_name = "cliente/carrito.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        carrito = obtener_carrito(self.request)
        ctx["carrito"] = carrito
        ctx["items"] = list(carrito.items.select_related("contenedor")) if carrito else []
        ctx["subtotal"] = sum(i.subtotal for i in ctx["items"])
        ctx["total"] = ctx["subtotal"]
        return ctx


@solo_clientes
@require_POST
def agregar_al_carrito(request, pk):
    contenedor = get_object_or_404(Contenedor, pk=pk, activo=True)
    cantidad = _entero(request.POST.get("cantidad", 1)) or 1
    try:
        agregar_item(obtener_carrito(request, crear=True), contenedor, cantidad)
        messages.success(request, f"«{contenedor.nombre}» se agregó al carrito.")
    except CarritoError as e:
        messages.warning(request, str(e))
    return _volver(request)


def _item_del_request(request, pk):
    # Solo ítems del carrito de quien hace la petición (evita tocar carritos ajenos por id).
    carrito = obtener_carrito(request)
    if carrito is None:
        raise Http404
    return get_object_or_404(ItemCarrito.objects.select_related("contenedor"), pk=pk, carrito=carrito)


@solo_clientes
@require_POST
def actualizar_cantidad(request, pk):
    item = _item_del_request(request, pk)
    try:
        actualizar_item(item, _entero(request.POST.get("cantidad"), defecto=item.cantidad))
    except CarritoError as e:
        messages.warning(request, str(e))
    return redirect("tienda:carrito")


@solo_clientes
@require_POST
def eliminar_item(request, pk):
    item = _item_del_request(request, pk)
    nombre = item.contenedor.nombre
    item.delete()
    messages.success(request, f"Quitaste «{nombre}» del carrito.")
    return redirect("tienda:carrito")


# ---------------------------------------------------------------------------
# C. Checkout: login obligatorio
# ---------------------------------------------------------------------------
class CheckoutView(SoloClientesMixin, LoginRequiredMixin, FormView):
    """Sin sesión -> /accounts/login/?next=/carrito/checkout/ y, tras entrar, vuelve aquí."""

    template_name = "cliente/checkout.html"
    form_class = CheckoutForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.carrito = obtener_carrito(request)
            if self.carrito is None or not self.carrito.items.exists():
                messages.info(request, "Tu carrito está vacío. Agrega un contenedor para continuar.")
                return redirect("catalogo")
        return super().dispatch(request, *args, **kwargs)

    def _cliente(self):
        return Cliente.objects.filter(usuario=self.request.user).first()

    def get_initial(self):
        user, cliente = self.request.user, self._cliente()
        return {
            "nombre": cliente.nombre if cliente else user.get_full_name(),
            "rut": cliente.rut if cliente else "",
            "razon_social": cliente.razon_social if cliente else "",
            "direccion_entrega": cliente.direccion if cliente else "",
            "telefono_contacto": cliente.telefono if cliente else "",
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        items = list(self.carrito.items.select_related("contenedor"))
        ctx["items"] = items
        ctx["total"] = sum(i.subtotal for i in items)
        return ctx

    def form_valid(self, form):
        d = form.cleaned_data
        user = self.request.user
        cliente = self._cliente() or Cliente(usuario=user, email=user.email)
        cliente.nombre = d["nombre"]
        cliente.rut = d["rut"]
        cliente.razon_social = d["razon_social"]
        cliente.telefono = d["telefono_contacto"]
        cliente.direccion = d["direccion_entrega"]
        cliente.save()
        try:
            pedido = crear_pedido(self.carrito, cliente, d)
        except PedidoError as e:
            messages.error(self.request, str(e))
            return redirect("tienda:carrito")
        return redirect("tienda:confirmacion", pk=pedido.pk)


# ---------------------------------------------------------------------------
# Pedidos del cliente
# ---------------------------------------------------------------------------
class _PedidosDelUsuario(LoginRequiredMixin):
    def get_queryset(self):
        return (
            Pedido.objects.filter(cliente__usuario=self.request.user)
            .select_related("cliente")
            .prefetch_related("items__contenedor")
        )


class ConfirmacionView(_PedidosDelUsuario, DetailView):
    template_name = "cliente/confirmacion.html"
    context_object_name = "pedido"


class MisPedidosView(_PedidosDelUsuario, ListView):
    template_name = "cliente/mis_pedidos.html"
    context_object_name = "pedidos"
    paginate_by = 10


class MiPedidoDetalleView(_PedidosDelUsuario, DetailView):
    template_name = "cliente/detalle_pedido.html"
    context_object_name = "pedido"
