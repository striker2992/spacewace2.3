from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Cliente

DATOS = {
    "first_name": "Ana", "last_name": "Soto", "email": "ana@ejemplo.cl",
    "rut": "12.345.678-5", "telefono": "+56 9 1111 2222", "razon_social": "Soto SpA",
    "direccion": "Av. Siempre Viva 123", "password1": "una-clave-muy-larga-987", "password2": "una-clave-muy-larga-987",
}


class RegistroTests(TestCase):
    def test_crea_usuario_y_perfil_de_cliente_e_inicia_sesion(self):
        resp = self.client.post(reverse("registro"), DATOS)
        self.assertRedirects(resp, reverse("catalogo"), fetch_redirect_response=False)
        user = get_user_model().objects.get(email="ana@ejemplo.cl")
        self.assertEqual(user.username, "ana@ejemplo.cl")
        cliente = Cliente.objects.get(usuario=user)
        self.assertEqual((cliente.rut, cliente.razon_social, cliente.telefono), ("12.345.678-5", "Soto SpA", "+56 9 1111 2222"))
        self.assertEqual(cliente.nombre, "Ana Soto")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_respeta_next_hacia_checkout(self):
        resp = self.client.post(reverse("registro"), {**DATOS, "next": "/carrito/checkout/"})
        self.assertRedirects(resp, "/carrito/checkout/", fetch_redirect_response=False)

    def test_next_externo_se_ignora(self):
        resp = self.client.post(reverse("registro"), {**DATOS, "next": "https://malo.example/"})
        self.assertRedirects(resp, reverse("catalogo"), fetch_redirect_response=False)

    def test_correo_duplicado_es_rechazado(self):
        get_user_model().objects.create_user("otro", email="ana@ejemplo.cl", password="x-clave-123456")
        resp = self.client.post(reverse("registro"), DATOS)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Cliente.objects.exists())


class LoginConCorreoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("camila", email="Camila@Ejemplo.cl", password="una-clave-muy-larga-987")

    def test_entra_con_correo_sin_importar_mayusculas(self):
        self.assertTrue(self.client.login(username="camila@ejemplo.cl", password="una-clave-muy-larga-987"))

    def test_entra_con_usuario(self):
        self.assertTrue(self.client.login(username="camila", password="una-clave-muy-larga-987"))

    def test_clave_incorrecta(self):
        self.assertFalse(self.client.login(username="camila@ejemplo.cl", password="otra"))

    def test_correo_repetido_no_permite_adivinar_la_cuenta(self):
        get_user_model().objects.create_user("otra", email="camila@ejemplo.cl", password="una-clave-muy-larga-987")
        self.assertFalse(self.client.login(username="camila@ejemplo.cl", password="una-clave-muy-larga-987"))


class ClienteConCuentaTests(TestCase):
    """El equipo interno crea clientes y, si quiere, su acceso a la tienda."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_user("jefe", password="una-clave-muy-larga-987", is_staff=True)

    def setUp(self):
        self.client.force_login(self.staff)

    def datos(self, **extra):
        d = {"nombre": "Ferretería Sur", "rut": "76.111.222-8", "razon_social": "", "email": "compras@sur.cl",
             "telefono": "", "direccion": "", "informacion_general": "", "password1": "", "password2": ""}
        d.update(extra)
        return d

    def test_crea_cliente_sin_cuenta(self):
        self.client.post(reverse("clientes:crear"), self.datos())
        cliente = Cliente.objects.get(nombre="Ferretería Sur")
        self.assertIsNone(cliente.usuario)

    def test_crea_cliente_con_contrasena_y_puede_entrar(self):
        clave = "clave-segura-del-cliente-1"
        self.client.post(reverse("clientes:crear"), self.datos(password1=clave, password2=clave))
        cliente = Cliente.objects.get(nombre="Ferretería Sur")
        self.assertEqual(cliente.usuario.username, "compras@sur.cl")
        self.client.logout()
        self.assertTrue(self.client.login(username="compras@sur.cl", password=clave))

    def test_contrasenas_distintas_o_debiles_se_rechazan(self):
        resp = self.client.post(reverse("clientes:crear"), self.datos(password1="clave-segura-1", password2="otra-clave-2"))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(reverse("clientes:crear"), self.datos(password1="123", password2="123"))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Cliente.objects.exists())

    def test_correo_de_otra_cuenta_se_rechaza(self):
        get_user_model().objects.create_user("x", email="compras@sur.cl", password="una-clave-muy-larga-987")
        clave = "clave-segura-del-cliente-1"
        resp = self.client.post(reverse("clientes:crear"), self.datos(password1=clave, password2=clave))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Cliente.objects.exists())

    def test_editar_cambia_contrasena(self):
        clave = "clave-segura-del-cliente-1"
        self.client.post(reverse("clientes:crear"), self.datos(password1=clave, password2=clave))
        cliente = Cliente.objects.get()
        nueva = "otra-clave-segura-del-cliente-2"
        self.client.post(reverse("clientes:editar", args=[cliente.pk]), self.datos(password1=nueva, password2=nueva))
        cliente.usuario.refresh_from_db()
        self.assertTrue(cliente.usuario.check_password(nueva))
