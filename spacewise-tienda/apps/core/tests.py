from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.vendedores.models import Vendedor

PANTALLAS_INTERNAS = [
    "dashboard", "clientes:lista", "cotizaciones:lista",
    "contenedores:lista", "vendedores:pedidos",
]


class PantallasTests(TestCase):
    """Smoke test: cada pantalla interna responde 200 para el equipo y está cerrada al resto."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.staff = User.objects.create_user("tester", password="clave-de-prueba-123", is_staff=True)
        cls.cliente = User.objects.create_user("comprador", password="clave-de-prueba-123")
        cls.vendedor = User.objects.create_user("vende", password="clave-de-prueba-123")
        Vendedor.objects.create(user=cls.vendedor)

    def test_login_visible(self):
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)

    def test_pantallas_internas_piden_login(self):
        for nombre in PANTALLAS_INTERNAS:
            with self.subTest(nombre):
                resp = self.client.get(reverse(nombre))
                self.assertEqual(resp.status_code, 302)
                self.assertIn("/accounts/login/", resp["Location"])

    def test_cliente_registrado_no_entra_a_pantallas_internas(self):
        self.client.force_login(self.cliente)
        for nombre in PANTALLAS_INTERNAS + ["clientes:crear", "contenedores:crear", "cotizaciones:crear"]:
            with self.subTest(nombre):
                resp = self.client.get(reverse(nombre))
                self.assertRedirects(resp, reverse("catalogo"), fetch_redirect_response=False)

    def test_cliente_no_puede_cambiar_estados_ni_aprobar(self):
        self.client.force_login(self.cliente)
        resp = self.client.post(reverse("cotizaciones:estado", args=[1]), {"estado": "aprobada"})
        self.assertRedirects(resp, reverse("catalogo"), fetch_redirect_response=False)

    def test_pantallas_principales_para_personal(self):
        for usuario in (self.staff, self.vendedor):
            self.client.force_login(usuario)
            for nombre in PANTALLAS_INTERNAS + ["clientes:crear", "contenedores:crear", "cotizaciones:crear"]:
                with self.subTest(usuario=usuario.username, pantalla=nombre):
                    self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)

    def test_login_redirige_segun_rol(self):
        resp = self.client.post(reverse("login"), {"username": "tester", "password": "clave-de-prueba-123"})
        self.assertRedirects(resp, reverse("dashboard"), fetch_redirect_response=False)
        self.client.logout()
        resp = self.client.post(reverse("login"), {"username": "comprador", "password": "clave-de-prueba-123"})
        self.assertRedirects(resp, reverse("catalogo"), fetch_redirect_response=False)
