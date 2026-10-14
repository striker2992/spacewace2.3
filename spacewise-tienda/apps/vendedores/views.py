from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.core.mixins import FormularioMixin, PersonalRequeridoMixin, QueryStringMixin, personal_requerido
from apps.cotizaciones.models import Pedido
from apps.cotizaciones.servicios import PedidoError, cambiar_estado_pedido

from .forms import VendedorCrearForm, VendedorEditarForm
from .models import Vendedor


class VendedorLista(PersonalRequeridoMixin, ListView):
    model = Vendedor
    template_name = "vendedores/lista.html"
    context_object_name = "vendedores"

    def get_queryset(self):
        return Vendedor.objects.select_related("user")


class VendedorCrear(FormularioMixin, CreateView):
    model = Vendedor
    form_class = VendedorCrearForm
    success_url = reverse_lazy("vendedores:lista")
    success_message = "Vendedor creado."
    titulo = "Nuevo vendedor"


class VendedorEditar(FormularioMixin, UpdateView):
    model = Vendedor
    form_class = VendedorEditarForm
    success_url = reverse_lazy("vendedores:lista")
    success_message = "Vendedor actualizado."
    titulo = "Editar vendedor"


# ---------------------------------------------------------------------------
# D. Pedidos de la tienda: revisión y cambio de estado por el equipo interno
# ---------------------------------------------------------------------------
class PedidoLista(PersonalRequeridoMixin, QueryStringMixin, ListView):
    model = Pedido
    template_name = "admin_custom/lista_pedidos.html"
    context_object_name = "pedidos"
    paginate_by = 12

    def get_queryset(self):
        g = self.request.GET
        qs = Pedido.objects.select_related("cliente").prefetch_related("items")
        q = g.get("q", "").strip()
        estado = g.get("estado", "")
        desde, hasta = parse_date(g.get("desde", "")), parse_date(g.get("hasta", ""))
        if q:
            qs = qs.filter(
                Q(numero_pedido__icontains=q) | Q(cliente__nombre__icontains=q) | Q(cliente__rut__icontains=q)
            )
        if estado in Pedido.Estado.values:
            qs = qs.filter(estado=estado)
        if desde:
            qs = qs.filter(fecha_creacion__date__gte=desde)
        if hasta:
            qs = qs.filter(fecha_creacion__date__lte=hasta)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        g = self.request.GET
        ctx.update(
            q=g.get("q", ""), estado=g.get("estado", ""), desde=g.get("desde", ""),
            hasta=g.get("hasta", ""), estados=Pedido.Estado.choices,
        )
        return ctx


class PedidoDetalle(PersonalRequeridoMixin, DetailView):
    model = Pedido
    template_name = "admin_custom/detalle_pedido.html"
    context_object_name = "pedido"

    def get_queryset(self):
        return Pedido.objects.select_related("cliente__usuario").prefetch_related("items__contenedor")


@personal_requerido
@require_POST
def pedido_cambiar_estado(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    nuevo = request.POST.get("estado", "")
    if nuevo not in Pedido.Estado.values:
        messages.error(request, "Estado inválido.")
    else:
        try:
            cambiar_estado_pedido(pedido, nuevo)
            messages.success(request, f"{pedido.numero_pedido}: ahora está {pedido.get_estado_display().lower()}.")
        except PedidoError as e:
            messages.error(request, str(e))
    return redirect("vendedores:detalle_pedido", pk=pedido.pk)
