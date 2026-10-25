from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import FormView
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.core.mixins import BorrarMixin, FormularioMixin, PersonalRequeridoMixin, QueryStringMixin, es_personal

from .forms import ClienteForm, PerfilForm, RegistroForm
from .models import Cliente


class ClienteLista(PersonalRequeridoMixin, QueryStringMixin, ListView):
    model = Cliente
    template_name = "clientes/lista.html"
    context_object_name = "clientes"
    paginate_by = 10

    def get_queryset(self):
        qs = Cliente.objects.all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(nombre__icontains=q) | Q(rut__icontains=q) | Q(email__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class ClienteDetalle(PersonalRequeridoMixin, DetailView):
    model = Cliente
    template_name = "clientes/detalle.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cliente = self.object
        ctx["cotizaciones"] = cliente.cotizaciones.prefetch_related("items", "servicios")[:5]
        ctx["pedidos"] = cliente.pedidos.all()[:5]
        ctx["n_cotizaciones"] = cliente.cotizaciones.count()
        ctx["n_pedidos"] = cliente.pedidos.count()
        return ctx


class ClienteCrear(FormularioMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    success_message = "Cliente creado."
    titulo = "Nuevo cliente"

    def get_success_url(self):
        return reverse_lazy("clientes:lista") if not self.object else self.object.get_absolute_url()


class ClienteEditar(FormularioMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    success_message = "Cliente actualizado."
    titulo = "Editar cliente"

    def get_success_url(self):
        return self.object.get_absolute_url()


class ClienteEliminar(BorrarMixin, DeleteView):
    model = Cliente
    success_url = reverse_lazy("clientes:lista")
    success_message = "Cliente eliminado."


class RegistroView(FormView):
    """Crear cuenta de cliente. Al terminar inicia sesión y vuelve a `next` (p. ej. el checkout)."""

    template_name = "registration/register.html"
    form_class = RegistroForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.get_siguiente())
        return super().dispatch(request, *args, **kwargs)

    def get_siguiente(self):
        destino = self.request.POST.get("next") or self.request.GET.get("next") or ""
        if destino and url_has_allowed_host_and_scheme(
            destino, allowed_hosts={self.request.get_host()}, require_https=self.request.is_secure()
        ):
            return destino
        return "catalogo"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["next"] = self.request.POST.get("next") or self.request.GET.get("next") or ""
        return ctx

    def form_valid(self, form):
        user = form.save()
        # login() dispara user_logged_in -> se fusiona el carrito de la sesión con el del usuario.
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect(self.get_siguiente())


class PerfilView(LoginRequiredMixin, FormView):
    """UC-01 Gestionar perfil: datos personales y, para clientes, contacto y facturación."""

    template_name = "cuenta/perfil.html"
    form_class = PerfilForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(user=self.request.user, es_cliente=not es_personal(self.request.user))
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Tus datos se actualizaron.")
        return redirect("perfil")


class CambiarClaveView(auth_views.PasswordChangeView):
    """UC-01: cambio de contraseña (mantiene la sesión abierta)."""

    template_name = "form.html"
    success_url = reverse_lazy("perfil")
    extra_context = {"titulo": "Cambiar contraseña", "cancel_url": reverse_lazy("perfil")}

    def form_valid(self, form):
        messages.success(self.request, "Tu contraseña se cambió.")
        return super().form_valid(form)
