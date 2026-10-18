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


class EstadoContenedorTests(TestCase):
    """Disponible / arrendado / en mantenimiento: solo los disponibles se pueden comprar."""

    @classmethod
    def setUpTestData(cls):
        cls.libre = Contenedor.objects.create(nombre="Libre", tipo="20DC", precio=1000, stock=3)
        cls.arrendado = Contenedor.objects.create(nombre="Arrendado", tipo="40DC", precio=1000, stock=3, estado="arrendado")
        cls.taller = Contenedor.objects.create(nombre="En taller", tipo="40HC", precio=1000, stock=3, estado="mantenimiento")

    def test_catalogo_filtra_por_estado(self):
        resp = self.client.get(reverse("catalogo"), {"estado": "arrendado"})
        self.assertContains(resp, "Arrendado")
        self.assertNotContains(resp, "En taller")

    def test_catalogo_muestra_estado_y_bloquea_compra(self):
        resp = self.client.get(reverse("catalogo"))
        self.assertContains(resp, "En mantenimiento")
        self.assertFalse(self.arrendado.disponible)
        self.assertTrue(self.libre.disponible)

    def test_no_se_puede_agregar_al_carrito(self):
        self.client.post(reverse("tienda:agregar", args=[self.taller.pk]), {"cantidad": 1})
        resp = self.client.get(reverse("tienda:carrito"))
        self.assertNotContains(resp, "En taller")


class ServiciosYOficinasTests(TestCase):
    """Servicios adicionales en el catálogo y en las cotizaciones; contenedores tipo oficina."""

    @classmethod
    def setUpTestData(cls):
        from .models import Servicio

        User = get_user_model()
        cls.staff = User.objects.create_user("jefe", password="clave-de-prueba-123", is_staff=True)
        cls.oficina = Contenedor.objects.create(nombre="Oficina modular", tipo="20OF", precio=9000, stock=2)
        cls.dry = Contenedor.objects.create(nombre="Dry común", tipo="40DC", precio=5000, stock=2)
        cls.transporte = Servicio.objects.create(nombre="Transporte", precio=1200, unidad="km")
        cls.oculto = Servicio.objects.create(nombre="Servicio retirado", precio=10, activo=False)

    def test_catalogo_filtra_oficinas_y_muestra_servicios_activos(self):
        resp = self.client.get(reverse("catalogo"), {"tipo": "20OF"})
        self.assertContains(resp, "Oficina modular")
        self.assertNotContains(resp, "Dry común")
        self.assertContains(resp, "Transporte")
        self.assertNotContains(resp, "Servicio retirado")

    def test_crud_de_servicios(self):
        from .models import Servicio

        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("contenedores:servicio_lista")).status_code, 200)
        self.client.post(reverse("contenedores:servicio_crear"),
                         {"nombre": "Instalación", "precio": "3500", "unidad": "servicio", "descripcion": "", "activo": "on"})
        s = Servicio.objects.get(nombre="Instalación")
        self.client.post(reverse("contenedores:servicio_editar", args=[s.pk]),
                         {"nombre": "Instalación", "precio": "4000", "unidad": "servicio", "descripcion": ""})
        s.refresh_from_db()
        self.assertEqual((s.precio, s.activo), (4000, False))
        self.client.post(reverse("contenedores:servicio_eliminar", args=[s.pk]))
        self.assertFalse(Servicio.objects.filter(pk=s.pk).exists())

    def test_cotizacion_con_contenedor_y_servicio(self):
        from apps.clientes.models import Cliente
        from apps.cotizaciones.models import Cotizacion

        cliente = Cliente.objects.create(nombre="Obras Norte")
        self.client.force_login(self.staff)
        datos = {
            "cliente": cliente.pk, "fecha": "2026-10-18", "notas": "",
            "items-TOTAL_FORMS": "1", "items-INITIAL_FORMS": "0", "items-MIN_NUM_FORMS": "1", "items-MAX_NUM_FORMS": "1000",
            "items-0-contenedor": self.oficina.pk, "items-0-cantidad": "1", "items-0-precio_unitario": "",
            "servicios-TOTAL_FORMS": "1", "servicios-INITIAL_FORMS": "0", "servicios-MIN_NUM_FORMS": "0", "servicios-MAX_NUM_FORMS": "1000",
            "servicios-0-servicio": self.transporte.pk, "servicios-0-cantidad": "10", "servicios-0-precio_unitario": "",
        }
        resp = self.client.post(reverse("cotizaciones:crear"), datos)
        cot = Cotizacion.objects.get(cliente=cliente)
        self.assertRedirects(resp, cot.get_absolute_url(), fetch_redirect_response=False)
        self.assertEqual(cot.total, 9000 + 10 * 1200)
        self.assertContains(self.client.get(cot.get_absolute_url()), "Transporte")
