from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.core.mixins import BorrarMixin, FormularioMixin, PersonalRequeridoMixin, QueryStringMixin

from .forms import ContenedorForm
from .models import Contenedor


# ---------------------------------------------------------------------------
# Administración interna (solo personal)
# ---------------------------------------------------------------------------
class ContenedorLista(PersonalRequeridoMixin, QueryStringMixin, ListView):
    model = Contenedor
    template_name = "contenedores/lista.html"
    context_object_name = "contenedores"
    paginate_by = 10

    def get_queryset(self):
        qs = Contenedor.objects.all()
        q = self.request.GET.get("q", "").strip()
        tipo = self.request.GET.get("tipo", "")
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(ubicacion__icontains=q))
        if tipo in Contenedor.Tipo.values:
            qs = qs.filter(tipo=tipo)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["tipo"] = self.request.GET.get("tipo", "")
        ctx["tipos"] = Contenedor.Tipo.choices
        return ctx


class ContenedorCrear(FormularioMixin, CreateView):
    model = Contenedor
    form_class = ContenedorForm
    success_url = reverse_lazy("contenedores:lista")
    success_message = "Contenedor creado."
    titulo = "Nuevo contenedor"


class ContenedorEditar(FormularioMixin, UpdateView):
    model = Contenedor
    form_class = ContenedorForm
    success_url = reverse_lazy("contenedores:lista")
    success_message = "Contenedor actualizado."
    titulo = "Editar contenedor"


class ContenedorEliminar(BorrarMixin, DeleteView):
    model = Contenedor
    success_url = reverse_lazy("contenedores:lista")
    success_message = "Contenedor eliminado."


# ---------------------------------------------------------------------------
# Catálogo público (sin login)
# ---------------------------------------------------------------------------
def _decimal(valor):
    """Lee un número del querystring; si no es válido, lo ignora en vez de fallar."""
    try:
        n = Decimal(valor)
    except (InvalidOperation, TypeError):
        return None
    # tope razonable: evita desbordes en la base de datos con valores como 1e999999
    return n if n.is_finite() and 0 <= n <= Decimal(10**10) else None


class CatalogoView(QueryStringMixin, ListView):
    """Catálogo accesible para cualquiera. Filtros: texto, tipo, tamaño (20'/40'),
    estado (nuevo/usado), rango de precio y solo con stock."""

    model = Contenedor
    template_name = "contenedores/catalogo.html"
    context_object_name = "contenedores"
    paginate_by = 9

    TAMANOS = [("20", "20 pies"), ("40", "40 pies")]

    def get_queryset(self):
        g = self.request.GET
        qs = Contenedor.objects.filter(activo=True)
        q = g.get("q", "").strip()
        tipo = g.get("tipo", "")
        tamano = g.get("tamano", "")
        condicion = g.get("condicion", "")
        precio_min = _decimal(g.get("precio_min", ""))
        precio_max = _decimal(g.get("precio_max", ""))

        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))
        if tipo in Contenedor.Tipo.values:
            qs = qs.filter(tipo=tipo)
        if tamano in ("20", "40"):
            qs = qs.filter(tipo__startswith=tamano)  # códigos: 20DC, 40DC, 40HC, 40RF, 20OT
        if condicion in Contenedor.Condicion.values:
            qs = qs.filter(condicion=condicion)
        if precio_min is not None:
            qs = qs.filter(precio__gte=precio_min)
        if precio_max is not None:
            qs = qs.filter(precio__lte=precio_max)
        if g.get("disponibles") == "1":
            qs = qs.filter(stock__gt=0)
        return qs.order_by("precio", "nombre")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        g = self.request.GET
        ctx.update(
            q=g.get("q", ""),
            tipo=g.get("tipo", ""),
            tamano=g.get("tamano", ""),
            condicion=g.get("condicion", ""),
            precio_min=g.get("precio_min", ""),
            precio_max=g.get("precio_max", ""),
            solo_disponibles=g.get("disponibles") == "1",
            tipos=Contenedor.Tipo.choices,
            tamanos=self.TAMANOS,
            condiciones=Contenedor.Condicion.choices,
        )
        ctx["hay_filtros"] = any(
            [ctx["q"], ctx["tipo"], ctx["tamano"], ctx["condicion"],
             ctx["precio_min"], ctx["precio_max"], ctx["solo_disponibles"]]
        )
        return ctx


class ContenedorDetalleView(DetailView):
    """Ficha pública del contenedor: foto, precio, stock y especificaciones."""

    model = Contenedor
    template_name = "contenedores/detalle.html"
    context_object_name = "contenedor"

    def get_queryset(self):
        return Contenedor.objects.filter(activo=True)
