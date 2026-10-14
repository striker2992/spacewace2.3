from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.core.mixins import BorrarMixin, FormularioMixin, PersonalRequeridoMixin, QueryStringMixin
from apps.vendedores.models import Vendedor

from .forms import OperacionForm
from .models import Operacion


class OperacionLista(PersonalRequeridoMixin, QueryStringMixin, ListView):
    model = Operacion
    template_name = "operaciones/lista.html"
    context_object_name = "operaciones"
    paginate_by = 12

    def get_queryset(self):
        qs = Operacion.objects.select_related("cliente", "contenedor")
        q = self.request.GET.get("q", "").strip()
        estado = self.request.GET.get("estado", "")
        tipo = self.request.GET.get("tipo", "")
        if q:
            qs = qs.filter(Q(cliente__nombre__icontains=q) | Q(cliente__rut__icontains=q))
        if estado in Operacion.Estado.values:
            qs = qs.filter(estado=estado)
        if tipo in Operacion.Tipo.values:
            qs = qs.filter(tipo=tipo)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["estado"] = self.request.GET.get("estado", "")
        ctx["tipo"] = self.request.GET.get("tipo", "")
        ctx["estados"] = Operacion.Estado.choices
        ctx["tipos"] = Operacion.Tipo.choices
        return ctx


class OperacionCrear(FormularioMixin, CreateView):
    model = Operacion
    form_class = OperacionForm
    success_url = reverse_lazy("operaciones:lista")
    success_message = "Compra registrada."
    titulo = "Registrar compra"

    def form_valid(self, form):
        form.instance.vendedor = Vendedor.objects.filter(user=self.request.user).first()
        return super().form_valid(form)


class OperacionEditar(FormularioMixin, UpdateView):
    model = Operacion
    form_class = OperacionForm
    success_url = reverse_lazy("operaciones:lista")
    success_message = "Compra actualizada."
    titulo = "Editar compra"


class OperacionEliminar(BorrarMixin, DeleteView):
    model = Operacion
    success_url = reverse_lazy("operaciones:lista")
    success_message = "Registro eliminado."
