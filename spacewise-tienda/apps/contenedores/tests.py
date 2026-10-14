from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Contenedor


class CatalogoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_user(
            "tester", password="clave-de-prueba-123", is_staff=True
        )
        cls.nuevo20 = Contenedor.objects.create(
            nombre="Contenedor veinte nuevo", tipo="20DC", condicion="nuevo", precio=4200, stock=5
        )
        cls.usado40 = Contenedor.objects.create(
            nombre="Contenedor cuarenta usado", tipo="40DC", condicion="usado", precio=3000, stock=0
        )
        cls.reefer = Contenedor.objects.create(
            nombre="Contenedor refrigerado", tipo="40RF", condicion="usado", precio=14500, stock=2
        )
        cls.oculto = Contenedor.objects.create(
            nombre="Contenedor oculto", tipo="20DC", condicion="nuevo", precio=1, stock=1, activo=False
        )

    def get(self, **params):
        return self.client.get(reverse("catalogo"), params)

    def test_catalogo_es_publico(self):
        resp = self.get()
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Agregar al carrito")

    def test_muestra_solo_contenedores_activos(self):
        resp = self.get()
        self.assertContains(resp, "Contenedor veinte nuevo")
        self.assertContains(resp, "Contenedor cuarenta usado")
        self.assertNotContains(resp, "Contenedor oculto")

    def test_filtra_por_tipo(self):
        resp = self.get(tipo="40DC")
        self.assertContains(resp, "Contenedor cuarenta usado")
        self.assertNotContains(resp, "Contenedor veinte nuevo")

    def test_filtra_por_tamano(self):
        resp = self.get(tamano="40")
        self.assertContains(resp, "Contenedor cuarenta usado")
        self.assertContains(resp, "Contenedor refrigerado")
        self.assertNotContains(resp, "Contenedor veinte nuevo")

    def test_filtra_por_estado(self):
        resp = self.get(condicion="nuevo")
        self.assertContains(resp, "Contenedor veinte nuevo")
        self.assertNotContains(resp, "Contenedor cuarenta usado")

    def test_filtra_por_rango_de_precio(self):
        resp = self.get(precio_min="3500", precio_max="10000")
        self.assertContains(resp, "Contenedor veinte nuevo")
        self.assertNotContains(resp, "Contenedor cuarenta usado")
        self.assertNotContains(resp, "Contenedor refrigerado")

    def test_precio_invalido_se_ignora_sin_error(self):
        for valor in ("abc", "-5", "1e999999", "nan"):
            with self.subTest(valor):
                self.assertEqual(self.get(precio_min=valor, precio_max=valor).status_code, 200)

    def test_filtra_solo_con_stock(self):
        resp = self.get(disponibles="1")
        self.assertContains(resp, "Contenedor veinte nuevo")
        self.assertNotContains(resp, "Contenedor cuarenta usado")

    def test_detalle_publico_y_oculto_da_404(self):
        self.assertEqual(self.client.get(self.nuevo20.get_absolute_url()).status_code, 200)
        self.assertEqual(self.client.get(self.oculto.get_absolute_url()).status_code, 404)

    def test_boton_cotizar_solo_para_personal(self):
        self.assertNotContains(self.get(), "Cotizar")
        self.client.force_login(self.staff)
        self.assertContains(self.get(), "Cotizar")

    def test_cotizar_desde_catalogo_precarga_el_contenedor(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("cotizaciones:crear"), {"contenedor": self.nuevo20.pk})
        self.assertEqual(resp.status_code, 200)
        primer_item = resp.context["formset"].forms[0]
        self.assertEqual(primer_item.initial.get("contenedor"), self.nuevo20.pk)
