from django.contrib.auth import views as auth_views
from django.shortcuts import render, resolve_url

from apps.clientes.models import Cliente
from apps.core.mixins import es_personal, personal_requerido
from apps.cotizaciones.models import Cotizacion, Pedido
from apps.vendedores.models import Vendedor


@personal_requerido
def dashboard(request):
    """Panel del equipo interno: totales, resumen de cotizaciones y actividad reciente."""
    total_cot = Cotizacion.objects.count()

    def fila(estado, etiqueta, icono, tono):
        n = Cotizacion.objects.filter(estado=estado).count()
        pct = round(n * 100 / total_cot) if total_cot else 0
        return {"estado": estado, "etiqueta": etiqueta, "n": n, "pct": pct, "icono": icono, "tono": tono}

    resumen = [
        fila(Cotizacion.Estado.APROBADA, "Aprobadas", "file-text", "indigo"),
        fila(Cotizacion.Estado.RECHAZADA, "Rechazadas", "check", "green"),
        fila(Cotizacion.Estado.PENDIENTE, "Pendientes", "clock", "amber"),
    ]

    return render(
        request,
        "core/dashboard.html",
        {
            "clientes_total": Cliente.objects.count(),
            "cotizaciones_abiertas": Cotizacion.objects.filter(estado=Cotizacion.Estado.PENDIENTE).count(),
            # "Compras" = pedidos de la tienda que no se cancelaron.
            "compras_registradas": Pedido.objects.exclude(estado=Pedido.Estado.CANCELADO).count(),
            "vendedores_activos": Vendedor.objects.filter(user__is_active=True).count(),
            "pedidos_pendientes_total": Pedido.objects.filter(estado=Pedido.Estado.PENDIENTE).count(),
            "resumen": resumen,
            "recientes": Cotizacion.objects.select_related("cliente").prefetch_related("items")[:4],
            "ultimos_pedidos": Pedido.objects.select_related("cliente")[:8],
        },
    )


class LoginView(auth_views.LoginView):
    """Login con destino según el rol: equipo interno -> dashboard; clientes -> catálogo.

    Si viene `?next=` (p. ej. el checkout) siempre se respeta.
    """

    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        return resolve_url("dashboard" if es_personal(self.request.user) else "catalogo")
