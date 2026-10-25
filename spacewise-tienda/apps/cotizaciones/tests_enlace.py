from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.clientes.models import Cliente
from apps.contenedores.models import Contenedor

from .models import Cotizacion, CotizacionItem

CLAVE = "clave-de-prueba-123"


class EnlacePublicoTests(TestCase):
    """RQ05: ver el estado de una cotización con un enlace único, sin iniciar sesión."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user("ana@ejemplo.cl", email="ana@ejemplo.cl", password=CLAVE)
        cls.otro = User.objects.create_user("beto@ejemplo.cl", email="beto@ejemplo.cl", password=CLAVE)
        cls.staff = User.objects.create_user("jefe", password=CLAVE, is_staff=True)
        cls.cliente = Cliente.objects.create(
            usuario=cls.user, nombre="Ana Soto", rut="12.345.678-5", telefono="+56911112222", direccion="Calle Secreta 1",
        )
        cls.contenedor = Contenedor.objects.create(nombre="Dry 20", tipo="20DC", precio=4000, stock=5)

    def setUp(self):
        self.cot = Cotizacion.objects.create(cliente=self.cliente, estado="pendiente")
        CotizacionItem.objects.create(cotizacion=self.cot, contenedor=self.contenedor, cantidad=2, precio_unitario=3500)

    def test_cada_cotizacion_tiene_un_token_unico_y_largo(self):
        otra = Cotizacion.objects.create(cliente=self.cliente)
        self.assertGreaterEqual(len(self.cot.token), 20)
        self.assertNotEqual(self.cot.token, otra.token)

    def test_anonimo_ve_estado_y_detalle_sin_datos_personales(self):
        resp = self.client.get(self.cot.get_enlace_publico())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.cot.numero)
        self.assertContains(resp, "Pendiente")
        self.assertContains(resp, "Dry 20")
        self.assertEqual(resp.context["cotizacion"].total, 7000)
        for privado in ("Ana Soto", "12.345.678-5", "+56911112222", "Calle Secreta"):
            self.assertNotContains(resp, privado)
        self.assertNotContains(resp, "/pdf/")
        self.assertEqual(resp["X-Robots-Tag"], "noindex, nofollow")
        self.assertEqual(resp["Referrer-Policy"], "no-referrer")

    def test_token_invalido_da_404(self):
        self.assertEqual(self.client.get(reverse("cotizacion_publica", args=["no-existe"])).status_code, 404)
        self.assertEqual(self.client.get("/c/%s/" % str(self.cot.pk)).status_code, 404)  # el id no sirve

    def test_cliente_ve_y_renueva_su_enlace(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("tienda:detalle_cotizacion", args=[self.cot.pk]))
        self.assertContains(resp, self.cot.get_enlace_publico())
        viejo = self.cot.get_enlace_publico()
        self.client.post(reverse("tienda:renovar_enlace", args=[self.cot.pk]))
        self.cot.refresh_from_db()
        self.assertNotEqual(self.cot.get_enlace_publico(), viejo)
        self.assertEqual(self.client.get(viejo).status_code, 404)
        self.assertEqual(self.client.get(self.cot.get_enlace_publico()).status_code, 200)

    def test_otro_cliente_no_renueva_ni_anonimo(self):
        token = self.cot.token
        self.client.force_login(self.otro)
        self.assertEqual(self.client.post(reverse("tienda:renovar_enlace", args=[self.cot.pk])).status_code, 404)
        self.client.logout()
        resp = self.client.post(reverse("tienda:renovar_enlace", args=[self.cot.pk]))
        self.assertIn("/accounts/login/", resp["Location"])
        self.cot.refresh_from_db()
        self.assertEqual(self.cot.token, token)

    def test_equipo_ve_y_renueva_el_enlace(self):
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(self.cot.get_absolute_url()), self.cot.get_enlace_publico())
        token = self.cot.token
        resp = self.client.post(reverse("cotizaciones:renovar_enlace", args=[self.cot.pk]))
        self.assertRedirects(resp, self.cot.get_absolute_url(), fetch_redirect_response=False)
        self.cot.refresh_from_db()
        self.assertNotEqual(self.cot.token, token)

    def test_renovar_requiere_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("tienda:renovar_enlace", args=[self.cot.pk])).status_code, 405)

    def test_duenio_ve_acceso_a_su_cuenta(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(self.cot.get_enlace_publico()), "Ver en mi cuenta")
        self.client.force_login(self.otro)
        self.assertNotContains(self.client.get(self.cot.get_enlace_publico()), "Ver en mi cuenta")
