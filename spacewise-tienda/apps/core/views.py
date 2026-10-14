from django.contrib.auth import views as auth_views
from django.db.models import Q
from django.shortcuts import render, resolve_url

from apps.clientes.models import Cliente
from apps.core.mixins import es_personal, personal_requerido
from apps.cotizaciones.models import Cotizacion, Pedido
#from apps.operaciones.models import Operacion
#from apps.vendedores.models import Vendedor


@personal_requerido
def dashboard(request):
    total_cot = Cotizacion.objects.count()

    def pct(n):
        return round(n * 100 / total_cot) if total_cot else 0

    def fila(estado, etiqueta, icono, tono):
        n = Cotizacion.objects.filter(estado=estado).count()
        return {"estado": estado, "etiqueta": etiqueta, "n": n, "pct": pct(n), "icono": icono, "tono": tono}

    resumen = [
        fila(Cotizacion.Estado.APROBADA, "Aprobadas", "file-text", "indigo"),
        fila(Cotizacion.Estado.RECHAZADA, "Rechazadas", "check", "green"),
        fila(Cotizacion.Estado.PENDIENTE, "Pendientes", "clock", "amber"),
    ]

    recientes = (
        Cotizacion.objects.select_related("cliente").prefetch_related("items")[:4]
    )

    solicitudes = Operacion.objects.select_related("cliente")
    q = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "")
    if q:
        solicitudes = solicitudes.filter(
            Q(cliente__nombre__icontains=q) | Q(cliente__rut__icontains=q)
        )
    if estado in Operacion.Estado.values:
        solicitudes = solicitudes.filter(estado=estado)

    return render(
        request,
        "core/dashboard.html",
        {
            "clientes_total": Cliente.objects.count(),
            "cotizaciones_abiertas": Cotizacion.objects.filter(
                estado=Cotizacion.Estado.PENDIENTE
            ).count(),
            "compras_registradas": Operacion.objects.exclude(
                tipo=Operacion.Tipo.DEVOLUCION
            ).count(),
            "vendedores_activos": Vendedor.objects.filter(activo=True).count(),
            "pedidos_pendientes_total": Pedido.objects.filter(estado=Pedido.Estado.PENDIENTE).count(),
            "resumen": resumen,
            "recientes": recientes,
            "solicitudes": solicitudes[:8],
            "q": q,
            "estado": estado,
            "estados": Operacion.Estado.choices,
        },
    )


class LoginView(auth_views.LoginView):
    """Login con destino según el rol: equipo interno -> dashboard; clientes -> catálogo.

    Si viene `?next=` (p. ej. el checkout) siempre se respeta.
    """

    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        return resolve_url("admin:index" if es_personal(self.request.user) else "catalogo")
