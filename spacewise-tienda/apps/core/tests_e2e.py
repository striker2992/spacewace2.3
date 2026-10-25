"""Pruebas en un navegador real (Playwright): lo que no se puede comprobar solo con el servidor.

Son opcionales. Para correrlas:
    pip install playwright
    playwright install chromium
    python manage.py test --tag e2e
Si Playwright no está instalado, se saltan solas y el resto de las pruebas corre igual.
"""

import os
import unittest

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import tag

from apps.clientes.models import Cliente
from apps.contenedores.models import Contenedor
from apps.cotizaciones.models import Cotizacion, Pedido

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

CLAVE = "clave-de-prueba-123"
DATOS_CHECKOUT = {
    "nombre": "Ana Soto", "rut": "12.345.678-5", "direccion_entrega": "Av. Siempre Viva 123, Coronel",
    "telefono_contacto": "+56 9 1111 2222",
}


@tag("e2e")
@unittest.skipIf(sync_playwright is None, "Playwright no está instalado (pip install playwright)")
class NavegadorTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        # Playwright usa un event loop propio; el ORM en las pruebas es seguro aquí.
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
        super().setUpClass()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        super().tearDownClass()

    def setUp(self):
        User = get_user_model()
        self.ana = User.objects.create_user("ana@ejemplo.cl", email="ana@ejemplo.cl", password=CLAVE, first_name="Ana")
        self.beto = User.objects.create_user("beto@ejemplo.cl", email="beto@ejemplo.cl", password=CLAVE, first_name="Beto")
        self.staff = User.objects.create_user("jefe", password=CLAVE, is_staff=True)
        Cliente.objects.create(usuario=self.ana, nombre="Ana Soto", email="ana@ejemplo.cl", rut="12.345.678-5")
        Cliente.objects.create(usuario=self.beto, nombre="Beto Ruiz", email="beto@ejemplo.cl", rut="10.000.013-K")
        self.contenedor = Contenedor.objects.create(nombre="Dry 20", tipo="20DC", precio=4000, stock=5)
        self.contextos = []

    def tearDown(self):
        for ctx in self.contextos:
            ctx.close()

    # --- ayudas ---
    def pagina(self, ancho=1280, alto=900):
        ctx = self.browser.new_context(viewport={"width": ancho, "height": alto})
        self.contextos.append(ctx)
        return ctx.new_page()

    def entrar(self, page, usuario, clave=CLAVE):
        page.goto(self.live_server_url + "/accounts/login/")
        page.fill("input[name=username]", usuario)
        page.fill("input[name=password]", clave)
        with page.expect_navigation():
            page.click("button[type=submit]")

    def al_checkout(self, page, contenedor, cantidad=1):
        page.goto(f"{self.live_server_url}/catalogo/{contenedor.pk}/")
        page.fill("input[name=cantidad]", str(cantidad))
        with page.expect_navigation():
            page.click("text=Agregar al carrito")
        page.goto(self.live_server_url + "/carrito/checkout/")
        for campo, valor in DATOS_CHECKOUT.items():
            page.fill(f"[name={campo}]", valor)

    # --- UX-01 ---
    def test_responsive_sin_scroll_horizontal(self):
        cot = Cotizacion.objects.create(cliente=self.ana.cliente, estado="aprobada")
        rutas = {
            None: ["/catalogo/", f"/catalogo/{self.contenedor.pk}/", "/accounts/login/", "/accounts/registro/",
                   "/carrito/", f"/c/{cot.token}/", "/accounts/clave/olvide/"],
            "ana@ejemplo.cl": ["/cotizaciones/", f"/cotizaciones/{cot.pk}/", "/pedidos/", "/garantias/",
                               "/accounts/perfil/", "/cotizaciones/solicitar/"],
            "jefe": ["/panel/", "/panel/cotizaciones/", f"/panel/cotizaciones/{cot.pk}/", "/panel/garantias/",
                     "/panel/reportes/", "/panel/clientes/", "/panel/contenedores/", "/panel/pedidos/"],
        }
        problemas = []
        for ancho in (390, 768, 1280):
            for usuario, urls in rutas.items():
                page = self.pagina(ancho)
                if usuario:
                    self.entrar(page, usuario)
                for url in urls:
                    page.goto(self.live_server_url + url)
                    sobra = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
                    if sobra > 0:
                        problemas.append(f"{ancho}px {url}: {sobra}px de más")
        self.assertEqual(problemas, [])

    # --- SEG-01 ---
    def test_atras_despues_de_salir_no_muestra_datos(self):
        Pedido.objects.create(cliente=self.ana.cliente, direccion_entrega="x", telefono_contacto="1", total=1)
        page = self.pagina()
        self.entrar(page, "ana@ejemplo.cl")
        page.goto(self.live_server_url + "/pedidos/")
        self.assertIn("PED-", page.content())
        with page.expect_navigation():
            page.click("text=Salir")
        page.go_back()
        self.assertNotIn("PED-", page.content(), "La página con datos quedó visible con «Atrás» tras salir")
        page.reload()
        self.assertIn("/accounts/login/", page.url)

    # --- EDGE-01 ---
    def test_doble_clic_en_confirmar_pedido_crea_un_solo_pedido(self):
        page = self.pagina()
        self.entrar(page, "ana@ejemplo.cl")
        self.al_checkout(page, self.contenedor, 2)
        page.dblclick("text=Confirmar pedido")
        page.wait_for_url("**/gracias/")
        page.wait_for_timeout(500)  # por si llega un segundo envío
        self.assertEqual(Pedido.objects.count(), 1)
        self.contenedor.refresh_from_db()
        self.assertEqual(self.contenedor.stock, 3)
        # EDGE-03: recargar la confirmación no duplica.
        page.reload()
        self.assertEqual(Pedido.objects.count(), 1)

    # --- EDGE-04 ---
    def test_dos_clientes_y_la_ultima_unidad(self):
        Contenedor.objects.filter(pk=self.contenedor.pk).update(stock=1)
        ana, beto = self.pagina(), self.pagina()
        self.entrar(ana, "ana@ejemplo.cl")
        self.entrar(beto, "beto@ejemplo.cl")
        self.al_checkout(ana, self.contenedor)
        self.al_checkout(beto, self.contenedor)
        with ana.expect_navigation():
            ana.click("text=Confirmar pedido")
        with beto.expect_navigation():
            beto.click("text=Confirmar pedido")
        self.assertIn("/gracias/", ana.url)
        self.assertIn("Cambió la disponibilidad", beto.content())
        self.assertEqual(Pedido.objects.count(), 1)
        self.contenedor.refresh_from_db()
        self.assertEqual(self.contenedor.stock, 0)

    # --- SEG-07 ---
    def test_xss_no_se_ejecuta(self):
        ataque = '<script>window.__xss=1</script><img src=x onerror="window.__xss=1">'
        cot = Cotizacion.objects.create(
            cliente=self.ana.cliente, estado="solicitada", origen="web", notas=ataque, direccion_entrega="Coronel"
        )
        for usuario, url in (("ana@ejemplo.cl", f"/cotizaciones/{cot.pk}/"), ("jefe", f"/panel/cotizaciones/{cot.pk}/")):
            page = self.pagina()
            self.entrar(page, usuario)
            page.goto(self.live_server_url + url)
            self.assertIsNone(page.evaluate("window.__xss"), f"Se ejecutó código en {url}")
            self.assertIn("<script>window.__xss=1</script>", page.inner_text("main"))
