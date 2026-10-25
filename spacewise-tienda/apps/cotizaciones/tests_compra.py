from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.clientes.models import Cliente
from apps.contenedores.models import Contenedor, Servicio

from .models import Cotizacion, CotizacionItem, CotizacionServicio, Pedido
from .servicios import PedidoError, cambiar_estado_pedido, comprar_cotizacion
from .tests import CLAVE, DATOS_CHECKOUT


class CompraDesdeCotizacionTests(TestCase):
    """RQ06: el cliente compra su cotización aprobada con los precios valorizados."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user("ana", email="ana@ejemplo.cl", password=CLAVE)
        cls.otro = User.objects.create_user("beto", password=CLAVE)
        cls.staff = User.objects.create_user("jefe", password=CLAVE, is_staff=True)
        cls.cliente = Cliente.objects.create(usuario=cls.user, nombre="Ana Soto", rut="12.345.678-5")
        cls.contenedor = Contenedor.objects.create(nombre="Dry 20", tipo="20DC", precio=4000, stock=5)
        cls.servicio = Servicio.objects.create(nombre="Transporte", precio=1200, unidad="km")

    def setUp(self):
        # Precios valorizados distintos al catálogo: la compra debe respetarlos.
        self.cot = Cotizacion.objects.create(cliente=self.cliente, estado=Cotizacion.Estado.APROBADA)
        CotizacionItem.objects.create(cotizacion=self.cot, contenedor=self.contenedor, cantidad=2, precio_unitario=3500)
        CotizacionServicio.objects.create(cotizacion=self.cot, servicio=self.servicio, cantidad=10, precio_unitario=1000)

    def comprar(self, usuario=None, cot=None):
        self.client.force_login(usuario or self.user)
        return self.client.post(reverse("tienda:comprar_cotizacion", args=[(cot or self.cot).pk]), DATOS_CHECKOUT)

    def test_compra_crea_pedido_con_precios_de_la_cotizacion(self):
        resp = self.comprar()
        pedido = Pedido.objects.get()
        self.assertRedirects(resp, reverse("tienda:confirmacion", args=[pedido.pk]), fetch_redirect_response=False)
        self.assertEqual(pedido.cotizacion, self.cot)
        self.assertEqual(pedido.total, 2 * 3500 + 10 * 1000)
        item = pedido.items.get()
        self.assertEqual((item.cantidad, item.precio_unitario), (2, 3500))
        self.assertEqual(pedido.servicios.get().subtotal, 10000)
        self.contenedor.refresh_from_db()
        self.assertEqual(self.contenedor.stock, 3)

    def test_boton_comprar_solo_en_aprobadas_y_luego_ver_pedido(self):
        self.client.force_login(self.user)
        url = reverse("tienda:detalle_cotizacion", args=[self.cot.pk])
        self.assertContains(self.client.get(url), reverse("tienda:comprar_cotizacion", args=[self.cot.pk]))
        self.comprar()
        resp = self.client.get(url)
        self.assertNotContains(resp, reverse("tienda:comprar_cotizacion", args=[self.cot.pk]))
        self.assertContains(resp, Pedido.objects.get().numero_pedido)

    def test_formulario_muestra_resumen_de_la_cotizacion(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("tienda:comprar_cotizacion", args=[self.cot.pk]))
        self.assertContains(resp, self.cot.numero)
        self.assertContains(resp, "Transporte")
        self.assertContains(resp, "Volver a la cotización")

    def test_no_aprobada_no_se_compra(self):
        for estado in ("solicitada", "pendiente", "rechazada"):
            Cotizacion.objects.filter(pk=self.cot.pk).update(estado=estado)
            resp = self.comprar()
            self.assertRedirects(resp, reverse("tienda:detalle_cotizacion", args=[self.cot.pk]), fetch_redirect_response=False)
        self.assertFalse(Pedido.objects.exists())

    def test_no_se_compra_dos_veces_salvo_si_se_cancela(self):
        self.comprar()
        self.comprar()
        self.assertEqual(Pedido.objects.count(), 1)
        cambiar_estado_pedido(Pedido.objects.get(), Pedido.Estado.CANCELADO)
        self.comprar()
        self.assertEqual(Pedido.objects.count(), 2)

    def test_servicio_valida_dueno_y_estado(self):
        otro_cliente = Cliente.objects.create(usuario=self.otro, nombre="Beto")
        with self.assertRaises(PedidoError):
            comprar_cotizacion(self.cot, otro_cliente, DATOS_CHECKOUT)

    def test_otro_usuario_no_ve_ni_compra_la_cotizacion(self):
        resp = self.comprar(usuario=self.otro)
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(Pedido.objects.exists())

    def test_sin_stock_no_crea_pedido(self):
        Contenedor.objects.filter(pk=self.contenedor.pk).update(stock=1)
        resp = self.comprar()
        self.assertRedirects(resp, reverse("tienda:detalle_cotizacion", args=[self.cot.pk]), fetch_redirect_response=False)
        self.assertFalse(Pedido.objects.exists())

    def test_equipo_interno_no_compra(self):
        resp = self.comprar(usuario=self.staff)
        self.assertRedirects(resp, reverse("dashboard"), fetch_redirect_response=False)
        self.assertFalse(Pedido.objects.exists())

    def test_anonimo_va_al_login(self):
        resp = self.client.get(reverse("tienda:comprar_cotizacion", args=[self.cot.pk]))
        self.assertIn("/accounts/login/", resp["Location"])

    def test_cotizacion_comprada_no_se_edita_ni_cambia_estado(self):
        self.comprar()
        self.client.force_login(self.staff)
        self.client.post(reverse("cotizaciones:estado", args=[self.cot.pk]), {"estado": "rechazada"})
        self.cot.refresh_from_db()
        self.assertEqual(self.cot.estado, "aprobada")
        resp = self.client.get(reverse("cotizaciones:editar", args=[self.cot.pk]))
        self.assertRedirects(resp, self.cot.get_absolute_url(), fetch_redirect_response=False)
        detalle = self.client.get(self.cot.get_absolute_url())
        self.assertContains(detalle, Pedido.objects.get().numero_pedido)

    def test_pedido_muestra_servicios_y_origen(self):
        self.comprar()
        pedido = Pedido.objects.get()
        resp = self.client.get(reverse("tienda:detalle_pedido", args=[pedido.pk]))
        self.assertContains(resp, "Transporte")
        self.assertContains(resp, self.cot.numero)
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("vendedores:detalle_pedido", args=[pedido.pk]))
        self.assertContains(resp, "Transporte")
        self.assertContains(resp, self.cot.numero)
