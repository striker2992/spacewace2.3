from functools import wraps

from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import ProtectedError
from django.shortcuts import redirect


def es_personal(user):
    """True para el equipo interno: staff/superusuario o vendedor activo.

    Los clientes que se registran en la tienda NO son personal interno y no
    deben ver clientes, cotizaciones, compras, etc.
    """
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    # related_name de Vendedor.user = "vendedor_profile" (RelatedObjectDoesNotExist es AttributeError)
    vendedor = getattr(user, "vendedor_profile", None)
    return vendedor is not None


class PersonalRequeridoMixin(AccessMixin):
    """Solo equipo interno. Anónimos -> login; clientes -> catálogo con aviso."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not es_personal(request.user):
            messages.error(request, "Esa sección es solo para el equipo interno.")
            return redirect("catalogo")
        return super().dispatch(request, *args, **kwargs)


def personal_requerido(view):
    """Equivalente funcional de PersonalRequeridoMixin para vistas basadas en funciones."""

    @wraps(view)
    def envuelta(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(request.get_full_path())
        if not es_personal(request.user):
            messages.error(request, "Esa sección es solo para el equipo interno.")
            return redirect("catalogo")
        return view(request, *args, **kwargs)

    return envuelta


_MSG_SIN_COMPRAS = "Las cuentas del equipo interno no pueden realizar compras en la tienda."


def solo_clientes(view):
    """Bloquea carrito y checkout para el equipo interno (admins y vendedores): no compran."""

    @wraps(view)
    def envuelta(request, *args, **kwargs):
        if es_personal(request.user):
            messages.error(request, _MSG_SIN_COMPRAS)
            return redirect("dashboard")
        return view(request, *args, **kwargs)

    return envuelta


class SoloClientesMixin:
    """Equivalente de `solo_clientes` para vistas basadas en clases (va primero en la herencia)."""

    def dispatch(self, request, *args, **kwargs):
        if es_personal(request.user):
            messages.error(request, _MSG_SIN_COMPRAS)
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)


class QueryStringMixin:
    """Expone `qs` (querystring sin 'page') para conservar filtros al paginar."""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["qs"] = params.urlencode()
        return ctx


class _CancelUrlMixin:
    def get_cancel_url(self):
        # En CreateView (GET) self.object es None y get_success_url() falla si success_url
        # es un string: se usa directamente.
        if getattr(self, "success_url", None):
            return str(self.success_url)
        return self.get_success_url()


class FormularioMixin(PersonalRequeridoMixin, _CancelUrlMixin, SuccessMessageMixin):
    """Crear/editar con plantilla genérica form.html."""

    template_name = "form.html"
    titulo = ""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = self.titulo
        ctx["cancel_url"] = self.get_cancel_url()
        return ctx


class BorrarMixin(PersonalRequeridoMixin, _CancelUrlMixin, SuccessMessageMixin):
    template_name = "confirm_delete.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = self.get_cancel_url()
        return ctx

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "No se puede eliminar: tiene registros asociados (cotizaciones, compras o pedidos).",
            )
            return redirect(self.get_cancel_url())
