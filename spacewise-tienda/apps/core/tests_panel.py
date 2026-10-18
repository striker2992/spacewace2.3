from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.clientes.models import Cliente
from apps.contenedores.models import Contenedor
from apps.cotizaciones.models import Carrito
from apps.cotizaciones.servicios import PedidoError, crear_pedido


class PanelYComprasTests(TestCase):
    """El panel es solo para el equipo interno y el equipo interno no puede comprar."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user("jefe", password="clave-de-prueba-123", is_staff=True)
        cls.comprador = User.objects.create_user("comprador", password="clave-de-prueba-123")
        cls.contenedor = Contenedor.objects.create(
            nombre="Contenedor 20'", tipo="20DC", condicion="nuevo", precio=1000, stock=5
        )

    def test_panel_visible_para_admin(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bienvenido de nuevo")

    def test_panel_cerrado_a_clientes_y_anonimos(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertIn("/accounts/login/", resp["Location"])
        self.client.force_login(self.comprador)
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("catalogo"), fetch_redirect_response=False)

    def test_login_admin_va_al_panel(self):
        resp = self.client.post(reverse("login"), {"username": "jefe", "password": "clave-de-prueba-123"})
        self.assertRedirects(resp, reverse("dashboard"), fetch_redirect_response=False)

    def test_admin_no_puede_agregar_ni_ver_carrito(self):
        self.client.force_login(self.admin)
        resp = self.client.post(reverse("tienda:agregar", args=[self.contenedor.pk]), {"cantidad": 1})
        self.assertRedirects(resp, reverse("dashboard"), fetch_redirect_response=False)
        self.assertFalse(Carrito.objects.filter(usuario=self.admin).exists())
        self.assertRedirects(self.client.get(reverse("tienda:carrito")), reverse("dashboard"), fetch_redirect_response=False)

    def test_admin_no_ve_boton_de_compra(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("catalogo"))
        self.assertNotContains(resp, "Agregar al carrito")
        self.assertContains(resp, "Compra no disponible")

    def test_servicio_rechaza_pedido_de_admin(self):
        carrito = Carrito.objects.create(usuario=self.admin)
        carrito.items.create(contenedor=self.contenedor, cantidad=1)
        cliente = Cliente.objects.create(usuario=self.admin, nombre="Jefe")
        with self.assertRaises(PedidoError):
            crear_pedido(carrito, cliente, {"direccion_entrega": "x", "telefono_contacto": "1"})

    def test_cliente_sigue_pudiendo_comprar(self):
        self.client.force_login(self.comprador)
        self.client.post(reverse("tienda:agregar", args=[self.contenedor.pk]), {"cantidad": 1})
        self.assertEqual(self.client.get(reverse("tienda:carrito")).status_code, 200)
        self.assertEqual(self.client.get(reverse("tienda:checkout")).status_code, 200)
