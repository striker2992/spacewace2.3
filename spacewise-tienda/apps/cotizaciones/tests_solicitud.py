from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.clientes.models import Cliente
from apps.contenedores.models import Contenedor, Servicio

from .models import Cotizacion

CLAVE = "clave-de-prueba-123"


def datos_solicitud(contenedor=None, servicio=None, **extra):
    d = {
        "fecha_requerida": "2026-11-30", "direccion_entrega": "Ruta 160 km 12, Coronel", "notas": "Para bodega",
        "items-TOTAL_FORMS": "1" if contenedor else "0", "items-INITIAL_FORMS": "0",
        "items-MIN_NUM_FORMS": "1", "items-MAX_NUM_FORMS": "1000",
        "servicios-TOTAL_FORMS": "1" if servicio else "0", "servicios-INITIAL_FORMS": "0",
        "servicios-MIN_NUM_FORMS": "0", "servicios-MAX_NUM_FORMS": "1000",
    }
    if contenedor:
        d.update({"items-0-contenedor": contenedor.pk, "items-0-cantidad": "2"})
    if servicio:
        d.update({"servicios-0-servicio": servicio.pk, "servicios-0-cantidad": "30"})
    d.update(extra)
    return d


class SolicitudCotizacionTests(TestCase):
    """RQ09 formulario del cliente, RQ10 su historial y RQ13 la bandeja del equipo."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user("ana@ejemplo.cl", email="ana@ejemplo.cl", password=CLAVE)
        cls.otro = User.objects.create_user("beto@ejemplo.cl", email="beto@ejemplo.cl", password=CLAVE)
        cls.staff = User.objects.create_user("jefe", password=CLAVE, is_staff=True)
        cls.contenedor = Contenedor.objects.create(nombre="Dry 20", tipo="20DC", precio=4000, stock=5)
        cls.servicio = Servicio.objects.create(nombre="Transporte", precio=1200, unidad="km")

    def solicitar(self, usuario=None, **kw):
        self.client.force_login(usuario or self.user)
        return self.client.post(
            reverse("tienda:solicitar_cotizacion"), datos_solicitud(self.contenedor, self.servicio, **kw)
        )

    def test_cliente_solicita_y_queda_en_la_bandeja(self):
        resp = self.solicitar()
        cot = Cotizacion.objects.get()
        self.assertRedirects(resp, reverse("tienda:detalle_cotizacion", args=[cot.pk]), fetch_redirect_response=False)
        self.assertEqual((cot.estado, cot.origen), ("solicitada", "web"))
        self.assertEqual(cot.cliente.usuario, self.user)  # se crea su perfil de cliente si no tenía
        self.assertEqual(cot.total, 2 * 4000 + 30 * 1200)  # precios del catálogo como referencia
        self.assertEqual(str(cot.fecha_requerida), "2026-11-30")

        self.client.force_login(self.staff)
        resp = self.client.get(reverse("cotizaciones:lista"), {"estado": "solicitada"})
        self.assertContains(resp, cot.numero)
        self.assertContains(self.client.get(reverse("dashboard")), "por valorizar")

    def test_usa_el_perfil_de_cliente_existente(self):
        cliente = Cliente.objects.create(usuario=self.user, nombre="Ana Soto", rut="1-9")
        self.solicitar()
        self.assertEqual(Cotizacion.objects.get().cliente, cliente)
        self.assertEqual(Cliente.objects.count(), 1)

    def test_requiere_al_menos_un_contenedor(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse("tienda:solicitar_cotizacion"), datos_solicitud(None, self.servicio))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Cotizacion.objects.exists())

    def test_anonimo_va_al_login_y_equipo_no_solicita(self):
        resp = self.client.get(reverse("tienda:solicitar_cotizacion"))
        self.assertIn("/accounts/login/", resp["Location"])
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("tienda:solicitar_cotizacion"))
        self.assertRedirects(resp, reverse("dashboard"), fetch_redirect_response=False)

    def test_historial_muestra_estado_y_solo_las_propias(self):
        self.solicitar()
        cot = Cotizacion.objects.get()
        resp = self.client.get(reverse("tienda:mis_cotizaciones"))
        self.assertContains(resp, cot.numero)
        self.assertContains(resp, "Solicitada")

        self.client.force_login(self.otro)
        self.assertNotContains(self.client.get(reverse("tienda:mis_cotizaciones")), cot.numero)
        self.assertEqual(self.client.get(reverse("tienda:detalle_cotizacion", args=[cot.pk])).status_code, 404)

    def test_equipo_valoriza_y_el_cliente_ve_el_avance(self):
        self.solicitar()
        cot = Cotizacion.objects.get()
        self.client.force_login(self.staff)
        self.client.post(reverse("cotizaciones:estado", args=[cot.pk]), {"estado": "pendiente"})
        cot.refresh_from_db()
        self.assertEqual(cot.estado, "pendiente")

        self.client.force_login(self.user)
        resp = self.client.get(reverse("tienda:detalle_cotizacion", args=[cot.pk]))
        self.assertContains(resp, "en revisión para su aprobación")

        self.client.force_login(self.staff)
        self.client.post(reverse("cotizaciones:estado", args=[cot.pk]), {"estado": "aprobada"})
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse("tienda:mis_cotizaciones")), "Aprobada")


class PdfCotizacionTests(TestCase):
    """RQ02: el equipo descarga el PDF de cualquier cotización. RQ11: el cliente, solo si está aprobada."""

    @classmethod
    def setUpTestData(cls):
        from .models import CotizacionItem, CotizacionServicio

        User = get_user_model()
        cls.user = User.objects.create_user("ana@ejemplo.cl", email="ana@ejemplo.cl", password=CLAVE)
        cls.otro = User.objects.create_user("beto@ejemplo.cl", email="beto@ejemplo.cl", password=CLAVE)
        cls.staff = User.objects.create_user("jefe", password=CLAVE, is_staff=True)
        cliente = Cliente.objects.create(usuario=cls.user, nombre="Ana Soto", rut="12.345.678-5")
        contenedor = Contenedor.objects.create(nombre="Dry 20", tipo="20DC", precio=4000, stock=5)
        servicio = Servicio.objects.create(nombre="Transporte", precio=1200, unidad="km")
        cls.cot = Cotizacion.objects.create(cliente=cliente, estado="pendiente", notas="Entrega en obra")
        CotizacionItem.objects.create(cotizacion=cls.cot, contenedor=contenedor, cantidad=2, precio_unitario=4000)
        CotizacionServicio.objects.create(cotizacion=cls.cot, servicio=servicio, cantidad=10, precio_unitario=1200)

    def es_pdf(self, resp):
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertIn(f"cotizacion-{self.cot.numero}.pdf", resp["Content-Disposition"])
        self.assertTrue(resp.content.startswith(b"%PDF"))

    def test_equipo_descarga_pdf_en_cualquier_estado(self):
        self.client.force_login(self.staff)
        self.es_pdf(self.client.get(reverse("cotizaciones:pdf", args=[self.cot.pk])))

    def test_cliente_no_descarga_hasta_que_se_apruebe(self):
        self.client.force_login(self.user)
        url = reverse("tienda:pdf_cotizacion", args=[self.cot.pk])
        self.assertRedirects(self.client.get(url), reverse("tienda:detalle_cotizacion", args=[self.cot.pk]),
                             fetch_redirect_response=False)
        Cotizacion.objects.filter(pk=self.cot.pk).update(estado="aprobada")
        self.es_pdf(self.client.get(url))

    def test_otro_cliente_no_puede_descargarlo(self):
        Cotizacion.objects.filter(pk=self.cot.pk).update(estado="aprobada")
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(reverse("tienda:pdf_cotizacion", args=[self.cot.pk])).status_code, 404)

    def test_cliente_no_entra_al_pdf_interno(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("cotizaciones:pdf", args=[self.cot.pk]))
        self.assertRedirects(resp, reverse("catalogo"), fetch_redirect_response=False)

    def test_formato_de_pesos(self):
        from .pdf import pesos

        self.assertEqual(pesos(4200), "$4.200")
        self.assertEqual(pesos(1234567.4), "$1.234.567")
