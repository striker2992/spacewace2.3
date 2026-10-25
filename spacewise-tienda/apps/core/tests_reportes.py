from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.clientes.models import Cliente
from apps.contenedores.models import Contenedor
from apps.cotizaciones.models import Cotizacion, CotizacionItem, ItemPedido, Pedido

from . import reportes

CLAVE = "clave-de-prueba-123"


def en(anio, mes, dia, hora=12):
    return datetime(anio, mes, dia, hora, tzinfo=timezone.get_current_timezone())


class ReporteMensualTests(TestCase):
    """RQ14: volumen de ventas y cotizaciones procesadas por mes."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.staff = User.objects.create_user("jefe", password=CLAVE, is_staff=True)
        cls.user = User.objects.create_user("ana@ejemplo.cl", email="ana@ejemplo.cl", password=CLAVE)
        cls.ana = Cliente.objects.create(usuario=cls.user, nombre="Ana Soto")
        cls.beto = Cliente.objects.create(nombre="Beto Ruiz")
        cls.c20 = Contenedor.objects.create(nombre="Dry 20", tipo="20DC", precio=4000, stock=50)
        cls.c40 = Contenedor.objects.create(nombre="Dry 40", tipo="40DC", precio=6000, stock=50)

        def pedido(cliente, cuando, total, estado="pendiente", items=()):
            p = Pedido.objects.create(cliente=cliente, estado=estado, total=total, direccion_entrega="x", telefono_contacto="1")
            Pedido.objects.filter(pk=p.pk).update(fecha_creacion=cuando)  # auto_now_add no se puede fijar al crear
            for c, n in items:
                ItemPedido.objects.create(pedido=p, contenedor=c, cantidad=n, precio_unitario=c.precio)

        # Octubre 2026: 2 ventas válidas + 1 cancelada (no cuenta). Una el 1° a las 00:30 hora de Chile.
        pedido(cls.ana, en(2026, 10, 1, 0), 10000, items=[(cls.c20, 2)])
        pedido(cls.beto, en(2026, 10, 20), 20000, estado="completado", items=[(cls.c40, 1), (cls.c20, 1)])
        pedido(cls.beto, en(2026, 10, 21), 99999, estado="cancelado", items=[(cls.c40, 9)])
        # Septiembre 2026 (incluye el 30 a las 23:00, que sigue siendo septiembre en Chile)
        pedido(cls.ana, en(2026, 9, 30, 23), 15000)

        def cot(cuando, estado, items=()):
            c = Cotizacion.objects.create(cliente=cls.ana, fecha=cuando, estado=estado)
            for cont, n in items:
                CotizacionItem.objects.create(cotizacion=c, contenedor=cont, cantidad=n, precio_unitario=1)

        cot(date(2026, 10, 2), "aprobada", [(cls.c40, 1)])
        cot(date(2026, 10, 5), "aprobada", [(cls.c40, 2)])
        cot(date(2026, 10, 9), "rechazada", [(cls.c20, 5)])
        cot(date(2026, 10, 9), "solicitada", [(cls.c40, 1)])
        cot(date(2026, 9, 9), "aprobada")

    def test_resumen_del_mes(self):
        m = reportes.resumen_mes(2026, 10)
        self.assertEqual((m["pedidos"], m["ventas"]), (2, Decimal(30000)))
        self.assertEqual(m["ticket"], Decimal(15000))
        self.assertEqual((m["recibidas"], m["aprobadas"], m["rechazadas"], m["en_curso"]), (4, 2, 1, 1))
        self.assertEqual(m["tasa_aprobacion"], 67)  # 2 de 3 resueltas
        sep = reportes.resumen_mes(2026, 9)
        self.assertEqual((sep["pedidos"], sep["ventas"], sep["recibidas"]), (1, Decimal(15000), 1))

    def test_reporte_rankings_y_variacion(self):
        r = reportes.reporte(2026, 10)
        self.assertEqual(len(r["serie"]), 12)
        self.assertEqual(r["serie"][-1]["clave"], "2026-10")
        self.assertEqual(r["var_ventas"], 100)  # 30.000 vs 15.000
        self.assertEqual(r["var_cotizaciones"], 300)  # 4 vs 1
        self.assertEqual([(v["contenedor__nombre"], v["cantidad"]) for v in r["vendidos"]], [("Dry 20", 3), ("Dry 40", 1)])
        self.assertEqual(r["cotizados"][0]["contenedor__nombre"], "Dry 40")  # en 3 cotizaciones
        self.assertEqual(r["cotizados"][0]["cotizaciones"], 3)
        self.assertEqual([c["cliente__nombre"] for c in r["clientes"]], ["Beto Ruiz", "Ana Soto"])
        self.assertEqual(r["serie"][-1]["alto"], 100)

    def test_mes_sin_datos(self):
        r = reportes.reporte(2025, 1)
        self.assertEqual(r["actual"]["ventas"], 0)
        self.assertIsNone(r["actual"]["tasa_aprobacion"])
        self.assertIsNone(r["var_ventas"])

    def test_leer_mes(self):
        self.assertEqual(reportes.leer_mes("2026-03"), (2026, 3))
        for malo in ("", "2026-13", "abc", "2026-1", "9999-01"):
            self.assertEqual(reportes.leer_mes(malo), reportes.mes_actual())
        self.assertEqual(reportes.mover(2026, 1, -1), (2025, 12))
        self.assertEqual(reportes.mover(2026, 12, 1), (2027, 1))

    def test_pagina_y_csv(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("reportes"), {"mes": "2026-10"})
        self.assertContains(resp, "Reporte de octubre 2026")
        self.assertContains(resp, "Beto Ruiz")
        self.assertContains(resp, "+100% vs mes anterior")
        resp = self.client.get(reverse("reportes"), {"mes": "2026-10", "formato": "csv"})
        self.assertEqual(resp["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("reporte-spacewise-2026-10.csv", resp["Content-Disposition"])
        texto = resp.content.decode("utf-8-sig")
        self.assertIn("octubre 2026;2;30000;15000;4;2;1;1;67;0", texto)
        self.assertIn("Dry 20;3;2", texto)

    def test_solo_equipo_interno(self):
        resp = self.client.get(reverse("reportes"))
        self.assertIn("/accounts/login/", resp["Location"])
        self.client.force_login(self.user)
        resp = self.client.get(reverse("reportes"))
        self.assertRedirects(resp, reverse("catalogo"), fetch_redirect_response=False)
