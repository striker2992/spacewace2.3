"""RQ14: reporte mensual de ventas y cotizaciones procesadas.

Los meses se calculan en la zona horaria del sitio (America/Santiago) y se filtra por
rangos de fechas, sin funciones de fecha de la base: así funciona igual en MySQL aunque
no tenga cargadas sus tablas de zonas horarias.
"""

import re
from datetime import datetime
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.cotizaciones.models import Cotizacion, CotizacionItem, ItemPedido, Pedido
from apps.operaciones.models import Garantia

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def mes_actual():
    hoy = timezone.localdate()
    return hoy.year, hoy.month


def leer_mes(valor):
    """'2026-10' -> (2026, 10). Si no es válido o es futuro, el mes actual."""
    m = re.fullmatch(r"(\d{4})-(\d{2})", valor or "")
    if m and 1 <= int(m[2]) <= 12 and 2000 <= int(m[1]) and (int(m[1]), int(m[2])) <= mes_actual():
        return int(m[1]), int(m[2])
    return mes_actual()


def mover(anio, mes, delta):
    total = anio * 12 + (mes - 1) + delta
    return total // 12, total % 12 + 1


def rango(anio, mes):
    tz = timezone.get_current_timezone()
    sig = mover(anio, mes, 1)
    return datetime(anio, mes, 1, tzinfo=tz), datetime(sig[0], sig[1], 1, tzinfo=tz)


def resumen_mes(anio, mes):
    inicio, fin = rango(anio, mes)
    ventas = Pedido.objects.filter(fecha_creacion__gte=inicio, fecha_creacion__lt=fin).exclude(
        estado=Pedido.Estado.CANCELADO
    ).aggregate(n=Count("id"), total=Sum("total"))
    E = Cotizacion.Estado
    cot = Cotizacion.objects.filter(fecha__gte=inicio.date(), fecha__lt=fin.date()).aggregate(
        recibidas=Count("id"),
        aprobadas=Count("id", filter=Q(estado=E.APROBADA)),
        rechazadas=Count("id", filter=Q(estado=E.RECHAZADA)),
        en_curso=Count("id", filter=Q(estado__in=[E.SOLICITADA, E.PENDIENTE])),
    )
    total = ventas["total"] or Decimal(0)
    resueltas = cot["aprobadas"] + cot["rechazadas"]
    return {
        "anio": anio, "mes": mes, "clave": f"{anio}-{mes:02d}",
        "nombre": f"{MESES[mes - 1]} {anio}", "mes_corto": MESES_CORTOS[mes - 1], "anio_corto": str(anio)[2:],
        "pedidos": ventas["n"], "ventas": total,
        "ticket": total / ventas["n"] if ventas["n"] else Decimal(0),
        **cot,
        "procesadas": resueltas,
        "tasa_aprobacion": round(cot["aprobadas"] * 100 / resueltas) if resueltas else None,
        "garantias": Garantia.objects.filter(fecha_solicitud__gte=inicio, fecha_solicitud__lt=fin).count(),
    }


def opciones_mes(n=24):
    """Los últimos `n` meses (el actual primero) para el selector: [("2026-10", "octubre 2026"), ...]."""
    anio, mes = mes_actual()
    return [(f"{a}-{m:02d}", f"{MESES[m - 1]} {a}") for a, m in (mover(anio, mes, -i) for i in range(n))]


def variacion(actual, anterior):
    """Variación porcentual redondeada; None si no hay base para comparar."""
    if not anterior:
        return None
    return round((actual - anterior) * 100 / anterior)


def reporte(anio, mes, meses=12):
    inicio, fin = rango(anio, mes)
    serie = [resumen_mes(*mover(anio, mes, -i)) for i in range(meses - 1, -1, -1)]
    actual, anterior = serie[-1], serie[-2]
    maximo = max((m["ventas"] for m in serie), default=0) or 1
    for m in serie:
        m["alto"] = round(m["ventas"] * 100 / maximo, 1)

    vendidos = (
        ItemPedido.objects.filter(pedido__fecha_creacion__gte=inicio, pedido__fecha_creacion__lt=fin)
        .exclude(pedido__estado=Pedido.Estado.CANCELADO)
        .values("contenedor__nombre")
        .annotate(cantidad=Sum("cantidad"), pedidos=Count("pedido", distinct=True))
        .order_by("-cantidad", "contenedor__nombre")[:5]
    )
    cotizados = (
        CotizacionItem.objects.filter(cotizacion__fecha__gte=inicio.date(), cotizacion__fecha__lt=fin.date())
        .values("contenedor__nombre")
        .annotate(cantidad=Sum("cantidad"), cotizaciones=Count("cotizacion", distinct=True))
        .order_by("-cotizaciones", "-cantidad", "contenedor__nombre")[:5]
    )
    clientes = (
        Pedido.objects.filter(fecha_creacion__gte=inicio, fecha_creacion__lt=fin)
        .exclude(estado=Pedido.Estado.CANCELADO)
        .values("cliente__nombre")
        .annotate(pedidos=Count("id"), total=Sum("total"))
        .order_by("-total", "cliente__nombre")[:5]
    )
    return {
        "actual": actual,
        "anterior": anterior,
        "var_ventas": variacion(actual["ventas"], anterior["ventas"]),
        "var_cotizaciones": variacion(actual["recibidas"], anterior["recibidas"]),
        "serie": serie,
        "vendidos": list(vendidos),
        "cotizados": list(cotizados),
        "clientes": list(clientes),
    }
