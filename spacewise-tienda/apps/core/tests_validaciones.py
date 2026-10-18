from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.clientes.models import Cliente
from apps.contenedores.models import Contenedor, Servicio
from apps.core import validators as v


class ValidadoresTests(SimpleTestCase):
    def test_rut(self):
        self.assertEqual(v.validar_rut("12345678-5"), "12.345.678-5")
        self.assertEqual(v.validar_rut("12.345.678-5"), "12.345.678-5")
        self.assertEqual(v.validar_rut("7.654.321-6"), "7.654.321-6")
        for malo in ["12.345.678-9", "abc", "12345", "12.345.678-X", "-5"]:
            with self.subTest(malo), self.assertRaises(ValidationError):
                v.validar_rut(malo)

    def test_rut_con_k(self):
        self.assertEqual(v.validar_rut("10000013k"), "10.000.013-K")

    def test_telefono(self):
        self.assertEqual(v.validar_telefono("+56 9 1234 5678"), "+56 9 1234 5678")
        self.assertEqual(v.validar_telefono("912345678"), "912345678")
        for malo in ["9123abcd", "12-34-56-78", "1234", "+56 9 1234 5678 9999", "9 1234+5678"]:
            with self.subTest(malo), self.assertRaises(ValidationError):
                v.validar_telefono(malo)

    def test_nombre_persona(self):
        for bueno in ["Ana", "María José", "O'Higgins", "Jean-Luc", "Ñuñoa"]:
            self.assertTrue(v.validar_nombre_persona(bueno))
        for malo in ["Ana2", "Juan$", "123", "<script>"]:
            with self.subTest(malo), self.assertRaises(ValidationError):
                v.validar_nombre_persona(malo)

    def test_texto(self):
        for bueno in ["Contenedor 20' estándar", "Alimentos P&R", "Av. Costanera #1234, Coronel", "Construcciones S.A."]:
            self.assertTrue(v.validar_texto(bueno))
        for malo in ["<b>hola</b>", "precio=100", "12345", "$$$", "{x}"]:
            with self.subTest(malo), self.assertRaises(ValidationError):
                v.validar_texto(malo)

    def test_fecha_no_pasada(self):
        hoy = timezone.localdate()
        self.assertEqual(v.validar_fecha_no_pasada(hoy), hoy)
        with self.assertRaises(ValidationError):
            v.validar_fecha_no_pasada(hoy - timedelta(days=1))


class FormulariosRechazanDatosInvalidosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.staff = User.objects.create_user("jefe", password="clave-de-prueba-123", is_staff=True)
        cls.contenedor = Contenedor.objects.create(nombre="Dry 20", tipo="20DC", precio=4000, stock=5)

    def setUp(self):
        self.client.force_login(self.staff)

    def crear_contenedor(self, **extra):
        d = {"nombre": "Contenedor nuevo", "tipo": "40HC", "condicion": "nuevo", "estado": "disponible",
             "precio": "5000", "stock": "3", "ubicacion": "Coronel", "descripcion": "", "especificaciones": ""}
        d.update(extra)
        return self.client.post(reverse("contenedores:crear"), d)

    def test_contenedor_precio_y_stock(self):
        for campo, malo in [("precio", "-100"), ("precio", "0"), ("precio", "abc"), ("stock", "-1"), ("stock", "dos"),
                            ("stock", "1.5"), ("nombre", "12345"), ("nombre", "<script>")]:
            with self.subTest(campo=campo, valor=malo):
                resp = self.crear_contenedor(**{campo: malo})
                self.assertEqual(resp.status_code, 200)
                self.assertTrue(resp.context["form"].errors.get(campo))
        self.assertEqual(Contenedor.objects.count(), 1)

    def test_formulario_tiene_atributos_html(self):
        html = self.client.get(reverse("contenedores:crear")).content.decode()
        self.assertIn('name="precio"', html)
        self.assertIn('data-filtro="entero"', html)
        self.assertRegex(html, r'name="precio"[^>]*min="1"|min="1"[^>]*name="precio"')

    def test_servicio_precio_negativo_y_unidad_con_numeros(self):
        datos = {"nombre": "Transporte", "precio": "-5", "unidad": "km2", "descripcion": ""}
        resp = self.client.post(reverse("contenedores:servicio_crear"), datos)
        self.assertEqual(set(resp.context["form"].errors), {"precio", "unidad"})
        self.assertFalse(Servicio.objects.exists())

    def test_cliente_rut_telefono_y_nombre(self):
        datos = {"nombre": "Ferretería Sur", "rut": "11.111.111-2", "razon_social": "", "email": "",
                 "telefono": "9abc", "direccion": "", "informacion_general": "", "password1": "", "password2": ""}
        resp = self.client.post(reverse("clientes:crear"), datos)
        self.assertEqual(set(resp.context["form"].errors), {"rut", "telefono"})
        datos.update(rut="111111111", telefono="+56 9 1111 2222")
        self.client.post(reverse("clientes:crear"), datos)
        self.assertEqual(Cliente.objects.get().rut, "11.111.111-1")  # se guarda con formato estándar

    def test_cantidad_negativa_en_cotizacion(self):
        cliente = Cliente.objects.create(nombre="Obras Norte")
        datos = {
            "cliente": cliente.pk, "fecha": "2026-10-18", "notas": "",
            "items-TOTAL_FORMS": "1", "items-INITIAL_FORMS": "0", "items-MIN_NUM_FORMS": "1", "items-MAX_NUM_FORMS": "1000",
            "items-0-contenedor": self.contenedor.pk, "items-0-cantidad": "-2", "items-0-precio_unitario": "-10",
            "servicios-TOTAL_FORMS": "0", "servicios-INITIAL_FORMS": "0", "servicios-MIN_NUM_FORMS": "0", "servicios-MAX_NUM_FORMS": "1000",
        }
        resp = self.client.post(reverse("cotizaciones:crear"), datos)
        errores = resp.context["formset"].forms[0].errors
        self.assertIn("cantidad", errores)
        self.assertIn("precio_unitario", errores)


class RegistroYCheckoutTests(TestCase):
    def test_registro_rechaza_nombre_con_numeros_y_rut_invalido(self):
        datos = {"email": "ana@ejemplo.cl", "first_name": "Ana2", "last_name": "Soto", "rut": "12.345.678-0",
                 "telefono": "+56 9 1111 2222", "razon_social": "", "direccion": "",
                 "password1": "una-clave-muy-larga-987", "password2": "una-clave-muy-larga-987"}
        resp = self.client.post(reverse("registro"), datos)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(set(resp.context["form"].errors), {"first_name", "rut"})
        self.assertFalse(get_user_model().objects.exists())
