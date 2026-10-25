import csv

from django.contrib.auth import views as auth_views
from django.http import HttpResponse
from django.shortcuts import redirect, render, resolve_url

from apps.clientes.models import Cliente
from apps.contenedores.views import CatalogoView
from apps.core.mixins import es_personal, personal_requerido
from apps.cotizaciones.models import Cotizacion, Pedido
from apps.vendedores.models import Vendedor

from . import reportes


def inicio(request):
    """Página de entrada: el equipo interno va directo a su panel; clientes y visitas ven el catálogo."""
    if es_personal(request.user):
        return redirect("dashboard")
    return CatalogoView.as_view()(request)


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
        fila(Cotizacion.Estado.SOLICITADA, "Solicitadas por clientes", "users", "indigo"),
    ]

    return render(
        request,
        "core/dashboard.html",
        {
            "clientes_total": Cliente.objects.count(),
            "cotizaciones_abiertas": Cotizacion.objects.filter(
                estado__in=[Cotizacion.Estado.SOLICITADA, Cotizacion.Estado.PENDIENTE]
            ).count(),
            "solicitudes_total": Cotizacion.objects.filter(estado=Cotizacion.Estado.SOLICITADA).count(),
            # "Compras" = pedidos de la tienda que no se cancelaron.
            "compras_registradas": Pedido.objects.exclude(estado=Pedido.Estado.CANCELADO).count(),
            "vendedores_activos": Vendedor.objects.filter(user__is_active=True).count(),
            "pedidos_pendientes_total": Pedido.objects.filter(estado=Pedido.Estado.PENDIENTE).count(),
            "resumen": resumen,
            "recientes": Cotizacion.objects.select_related("cliente").prefetch_related("items", "servicios")[:4],
            "ultimos_pedidos": Pedido.objects.select_related("cliente")[:8],
        },
    )


@personal_requerido
def reporte_mensual(request):
    """RQ14: volumen de ventas y cotizaciones procesadas de un mes, con los últimos 12 meses."""
    anio, mes = reportes.leer_mes(request.GET.get("mes"))
    datos = reportes.reporte(anio, mes)
    if request.GET.get("formato") == "csv":
        return _reporte_csv(datos)
    actual = (anio, mes) == reportes.mes_actual()
    datos.update(
        mes_anterior="%d-%02d" % reportes.mover(anio, mes, -1),
        mes_siguiente=None if actual else "%d-%02d" % reportes.mover(anio, mes, 1),
        opciones_mes=reportes.opciones_mes(),
        es_mes_actual=actual,
    )
    return render(request, "core/reportes.html", datos)


def _reporte_csv(datos):
    a = datos["actual"]
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="reporte-spacewise-{a["clave"]}.csv"'
    resp.write("\ufeff")  # BOM: Excel reconoce los acentos
    w = csv.writer(resp, delimiter=";")  # Excel en español separa con punto y coma
    w.writerow([f"Reporte mensual SpaceWise - {a['nombre']}"])
    w.writerow([])
    w.writerow(["Mes", "Pedidos", "Ventas", "Ticket promedio", "Cotizaciones recibidas",
                "Aprobadas", "Rechazadas", "En curso", "Tasa de aprobación (%)", "Garantías"])
    for m in reversed(datos["serie"]):
        w.writerow([m["nombre"], m["pedidos"], round(m["ventas"]), round(m["ticket"]), m["recibidas"],
                    m["aprobadas"], m["rechazadas"], m["en_curso"],
                    "" if m["tasa_aprobacion"] is None else m["tasa_aprobacion"], m["garantias"]])
    w.writerow([])
    w.writerow([f"Contenedores más vendidos - {a['nombre']}"])
    w.writerow(["Contenedor", "Unidades", "Pedidos"])
    for v in datos["vendidos"]:
        w.writerow([v["contenedor__nombre"], v["cantidad"], v["pedidos"]])
    w.writerow([])
    w.writerow([f"Contenedores más cotizados - {a['nombre']}"])
    w.writerow(["Contenedor", "Cotizaciones", "Unidades"])
    for c in datos["cotizados"]:
        w.writerow([c["contenedor__nombre"], c["cotizaciones"], c["cantidad"]])
    w.writerow([])
    w.writerow([f"Clientes frecuentes - {a['nombre']}"])
    w.writerow(["Cliente", "Pedidos", "Total"])
    for c in datos["clientes"]:
        w.writerow([c["cliente__nombre"], c["pedidos"], round(c["total"] or 0)])
    return resp


class LoginView(auth_views.LoginView):
    """Login con destino según el rol: equipo interno -> dashboard; clientes -> catálogo.

    Si viene `?next=` (p. ej. el checkout) siempre se respeta.
    """

    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        return resolve_url("dashboard" if es_personal(self.request.user) else "catalogo")
