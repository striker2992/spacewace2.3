from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import DeleteView, DetailView, ListView

from apps.core.mixins import BorrarMixin, PersonalRequeridoMixin, QueryStringMixin, personal_requerido
from apps.operaciones.models import Operacion
from apps.vendedores.models import Vendedor

from .forms import CotizacionForm, ItemFormSet
from .models import Cotizacion


class CotizacionLista(PersonalRequeridoMixin, QueryStringMixin, ListView):
    model = Cotizacion
    template_name = "cotizaciones/lista.html"
    context_object_name = "cotizaciones"
    paginate_by = 10

    def get_queryset(self):
        qs = (
            Cotizacion.objects.select_related("cliente", "vendedor__user")
            .prefetch_related("items")
        )
        q = self.request.GET.get("q", "").strip()
        estado = self.request.GET.get("estado", "")
        if q:
            qs = qs.filter(Q(cliente__nombre__icontains=q) | Q(cliente__rut__icontains=q))
        if estado in Cotizacion.Estado.values:
            qs = qs.filter(estado=estado)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["estado"] = self.request.GET.get("estado", "")
        ctx["estados"] = Cotizacion.Estado.choices
        return ctx


class CotizacionDetalle(PersonalRequeridoMixin, DetailView):
    model = Cotizacion
    template_name = "cotizaciones/detalle.html"

    def get_queryset(self):
        return Cotizacion.objects.select_related("cliente", "vendedor__user").prefetch_related(
            "items__contenedor"
        )


def _guardar(request, instance=None):
    if request.method == "POST":
        form = CotizacionForm(request.POST, instance=instance)
        formset = ItemFormSet(request.POST, instance=form.instance)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                cot = form.save(commit=False)
                if instance is None:
                    cot.vendedor = Vendedor.objects.filter(user=request.user).first()
                cot.save()
                formset.instance = cot
                formset.save()
            messages.success(request, "Cotización guardada.")
            return redirect(cot)
    else:
        form = CotizacionForm(instance=instance)
        initial_items = None
        contenedor_id = request.GET.get("contenedor", "")
        if instance is None and contenedor_id.isdigit():
            # Viene del catálogo: precarga ese contenedor como primer ítem
            initial_items = [{"contenedor": int(contenedor_id)}]
        formset = ItemFormSet(instance=form.instance, initial=initial_items)

    return render(
        request,
        "cotizaciones/form.html",
        {
            "form": form,
            "formset": formset,
            "titulo": "Editar cotización" if instance else "Nueva cotización",
            "cancel_url": instance.get_absolute_url() if instance else reverse_lazy("cotizaciones:lista"),
        },
    )


@personal_requerido
def cotizacion_crear(request):
    return _guardar(request)


@personal_requerido
def cotizacion_editar(request, pk):
    return _guardar(request, get_object_or_404(Cotizacion, pk=pk))


@personal_requerido
@require_POST
def cotizacion_estado(request, pk):
    cot = get_object_or_404(Cotizacion, pk=pk)
    nuevo = request.POST.get("estado")
    if nuevo not in Cotizacion.Estado.values:
        return HttpResponseBadRequest("Estado inválido")

    with transaction.atomic():
        cot.estado = nuevo
        cot.save(update_fields=["estado"])
        # Al aprobar, se registra una compra pendiente por cada ítem (solo una vez)
        if nuevo == Cotizacion.Estado.APROBADA and not cot.operaciones.exists():
            for item in cot.items.select_related("contenedor"):
                Operacion.objects.create(
                    cliente=cot.cliente,
                    tipo=Operacion.Tipo.VENTA,
                    cantidad=item.cantidad,
                    estado=Operacion.Estado.PENDIENTE,
                    contenedor=item.contenedor,
                    cotizacion=cot,
                    vendedor=cot.vendedor,
                )
    messages.success(request, f"Cotización {cot.numero}: {cot.get_estado_display().lower()}.")
    return redirect(cot)


class CotizacionEliminar(BorrarMixin, DeleteView):
    model = Cotizacion
    success_url = reverse_lazy("cotizaciones:lista")
    success_message = "Cotización eliminada."
