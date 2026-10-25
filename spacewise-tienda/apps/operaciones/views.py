"""RQ12 / UC-08: el cliente solicita garantías de sus pedidos y el equipo las resuelve."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from apps.core.mixins import PersonalRequeridoMixin, QueryStringMixin, SoloClientesMixin, personal_requerido, solo_clientes
from apps.cotizaciones.models import Pedido

from .forms import ResolverGarantiaForm, SolicitudGarantiaForm
from .models import Garantia
from .servicios import GarantiaError, resolver_garantia, solicitar_garantia


def _garantias():
    return Garantia.objects.select_related("pedido__cliente", "resuelta_por").prefetch_related("items__contenedor")


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------
@login_required
@solo_clientes
def solicitar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk, cliente__usuario=request.user)
    if not pedido.admite_garantia:
        messages.info(request, pedido.motivo_sin_garantia)
        return redirect(pedido)
    form = SolicitudGarantiaForm(request.POST or None, pedido=pedido)
    if request.method == "POST" and form.is_valid():
        try:
            garantia = solicitar_garantia(pedido, form.cleaned_data["motivo"], form.cantidades())
        except GarantiaError as e:
            messages.error(request, str(e))
            return redirect(pedido)
        messages.success(request, f"Recibimos tu solicitud {garantia.numero}. Te avisaremos cuando la revisemos.")
        return redirect("garantias:mi_garantia", pk=garantia.pk)
    return render(request, "operaciones/solicitar.html", {"form": form, "pedido": pedido})


class _GarantiasDelUsuario(SoloClientesMixin, LoginRequiredMixin):
    def get_queryset(self):
        return _garantias().filter(pedido__cliente__usuario=self.request.user)


class MisGarantiasView(_GarantiasDelUsuario, ListView):
    template_name = "operaciones/mis_garantias.html"
    context_object_name = "garantias"
    paginate_by = 10


class MiGarantiaDetalleView(_GarantiasDelUsuario, DetailView):
    template_name = "operaciones/mi_garantia.html"
    context_object_name = "garantia"


# ---------------------------------------------------------------------------
# Equipo interno
# ---------------------------------------------------------------------------
class GarantiaLista(PersonalRequeridoMixin, QueryStringMixin, ListView):
    template_name = "operaciones/lista.html"
    context_object_name = "garantias"
    paginate_by = 10

    def get_queryset(self):
        qs = _garantias()
        q = self.request.GET.get("q", "").strip()
        estado = self.request.GET.get("estado", "")
        if q:
            qs = qs.filter(
                Q(pedido__cliente__nombre__icontains=q) | Q(pedido__cliente__rut__icontains=q)
                | Q(pedido__numero_pedido__icontains=q)
            )
        if estado in Garantia.Estado.values:
            qs = qs.filter(estado=estado)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["estado"] = self.request.GET.get("estado", "")
        ctx["estados"] = Garantia.Estado.choices
        ctx["por_estado"] = [
            {"valor": v, "etiqueta": e, "n": Garantia.objects.filter(estado=v).count()}
            for v, e in Garantia.Estado.choices
        ]
        return ctx


class GarantiaDetalle(PersonalRequeridoMixin, DetailView):
    template_name = "operaciones/detalle.html"
    context_object_name = "garantia"

    def get_queryset(self):
        return _garantias()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault("form", ResolverGarantiaForm())
        return ctx


@personal_requerido
@require_POST
def resolver(request, pk):
    garantia = get_object_or_404(_garantias(), pk=pk)
    form = ResolverGarantiaForm(request.POST)
    if not form.is_valid():
        return render(request, "operaciones/detalle.html", {"garantia": garantia, "form": form}, status=400)
    try:
        garantia = resolver_garantia(garantia, form.cleaned_data["estado"], form.cleaned_data["resolucion"], request.user)
    except GarantiaError as e:
        messages.error(request, str(e))
    else:
        messages.success(request, f"Garantía {garantia.numero}: {garantia.get_estado_display().lower()}.")
    return redirect(garantia)
