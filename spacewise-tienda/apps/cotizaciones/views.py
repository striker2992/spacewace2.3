from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import DeleteView, DetailView, ListView

from apps.core.mixins import BorrarMixin, PersonalRequeridoMixin, QueryStringMixin, personal_requerido
from apps.vendedores.models import Vendedor

from .forms import CotizacionForm, ItemFormSet, ServicioFormSet
from .models import Cotizacion
from .pdf import respuesta_pdf


class CotizacionLista(PersonalRequeridoMixin, QueryStringMixin, ListView):
    model = Cotizacion
    template_name = "cotizaciones/lista.html"
    context_object_name = "cotizaciones"
    paginate_by = 10

    def get_queryset(self):
        qs = (
            Cotizacion.objects.select_related("cliente", "vendedor__user")
            .prefetch_related("items", "servicios")
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
        # Bandeja: cantidad por estado (las solicitadas son las que esperan valorización)
        ctx["por_estado"] = [
            {"valor": v, "etiqueta": e, "n": Cotizacion.objects.filter(estado=v).count()}
            for v, e in Cotizacion.Estado.choices
        ]
        return ctx


class CotizacionDetalle(PersonalRequeridoMixin, DetailView):
    model = Cotizacion
    template_name = "cotizaciones/detalle.html"

    def get_queryset(self):
        return Cotizacion.objects.select_related("cliente", "vendedor__user").prefetch_related(
            "items__contenedor", "servicios__servicio"
        )


def _guardar(request, instance=None):
    if request.method == "POST":
        form = CotizacionForm(request.POST, instance=instance)
        formset = ItemFormSet(request.POST, instance=form.instance)
        servicios = ServicioFormSet(request.POST, instance=form.instance, prefix="servicios")
        if form.is_valid() and formset.is_valid() and servicios.is_valid():
            with transaction.atomic():
                cot = form.save(commit=False)
                if instance is None:
                    cot.vendedor = Vendedor.objects.filter(user=request.user).first()
                cot.save()
                formset.instance = cot
                formset.save()
                servicios.instance = cot
                servicios.save()
            messages.success(request, "Cotización guardada.")
            return redirect(cot)
    else:
        # Desde la ficha del cliente llega ?cliente=<id> para dejarlo preseleccionado
        cliente_id = request.GET.get("cliente", "")
        inicial = {"cliente": int(cliente_id)} if instance is None and cliente_id.isdigit() else None
        form = CotizacionForm(instance=instance, initial=inicial)
        initial_items = None
        contenedor_id = request.GET.get("contenedor", "")
        if instance is None and contenedor_id.isdigit():
            # Viene del catálogo: precarga ese contenedor como primer ítem
            initial_items = [{"contenedor": int(contenedor_id)}]
        formset = ItemFormSet(instance=form.instance, initial=initial_items)
        servicios = ServicioFormSet(instance=form.instance, prefix="servicios")

    return render(
        request,
        "cotizaciones/form.html",
        {
            "form": form,
            "formset": formset,
            "servicios": servicios,
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

    cot.estado = nuevo
    cot.save(update_fields=["estado"])
    messages.success(request, f"Cotización {cot.numero}: {cot.get_estado_display().lower()}.")
    return redirect(cot)


class CotizacionEliminar(BorrarMixin, DeleteView):
    model = Cotizacion
    success_url = reverse_lazy("cotizaciones:lista")
    success_message = "Cotización eliminada."


@personal_requerido
def cotizacion_pdf(request, pk):
    """RQ02: documento formal para enviar al cliente."""
    cot = get_object_or_404(
        Cotizacion.objects.select_related("cliente", "vendedor__user").prefetch_related(
            "items__contenedor", "servicios__servicio"
        ),
        pk=pk,
    )
    return respuesta_pdf(request, cot, cot.get_absolute_url())
