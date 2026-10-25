from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Cliente

CLAVE = "clave-de-prueba-123"
DATOS = {
    "first_name": "Ana", "last_name": "Soto", "email": "ana.nueva@ejemplo.cl", "rut": "12.345.678-5",
    "telefono": "+56911112222", "razon_social": "Soto SpA", "direccion": "Av. Siempre Viva 123",
}


class PerfilTests(TestCase):
    """UC-01: el usuario ve y edita sus datos y cambia su contraseña."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user("ana@ejemplo.cl", email="ana@ejemplo.cl", password=CLAVE)
        cls.cliente = Cliente.objects.create(usuario=cls.user, nombre="Ana", email="ana@ejemplo.cl", rut="1-9")
        cls.staff = User.objects.create_user("jefe", password=CLAVE, is_staff=True, first_name="Jefe")
        User.objects.create_user("otra@ejemplo.cl", email="otra@ejemplo.cl", password=CLAVE)

    def test_requiere_login(self):
        resp = self.client.get(reverse("perfil"))
        self.assertIn("/accounts/login/", resp["Location"])

    def test_muestra_los_datos_actuales(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("perfil"))
        self.assertContains(resp, 'value="ana@ejemplo.cl"')
        self.assertContains(resp, 'value="1-9"')

    def test_cliente_actualiza_cuenta_y_ficha(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse("perfil"), DATOS)
        self.assertRedirects(resp, reverse("perfil"), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.cliente.refresh_from_db()
        # El correo es el dato de acceso: cambia también el nombre de usuario.
        self.assertEqual((self.user.username, self.user.email), ("ana.nueva@ejemplo.cl", "ana.nueva@ejemplo.cl"))
        self.assertEqual(self.cliente.nombre, "Ana Soto")
        self.assertEqual((self.cliente.email, self.cliente.razon_social), ("ana.nueva@ejemplo.cl", "Soto SpA"))
        self.assertEqual(self.cliente.rut, "12.345.678-5")
        self.assertTrue(self.client.login(username="ana.nueva@ejemplo.cl", password=CLAVE))

    def test_crea_la_ficha_si_no_existe(self):
        self.cliente.delete()
        self.client.force_login(self.user)
        self.client.post(reverse("perfil"), DATOS)
        self.assertEqual(Cliente.objects.get(usuario=self.user).telefono, "+56911112222")

    def test_valida_rut_y_correo_repetido(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse("perfil"), {**DATOS, "rut": "12.345.678-9", "email": "otra@ejemplo.cl"})
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp.context["form"], "email", "Ya existe una cuenta con ese correo.")
        self.assertTrue(resp.context["form"].errors.get("rut"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "ana@ejemplo.cl")

    def test_equipo_interno_edita_solo_sus_datos(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("perfil"))
        self.assertNotContains(resp, 'name="rut"')
        self.client.post(reverse("perfil"), {"first_name": "Juan", "last_name": "Pérez", "email": ""})
        self.staff.refresh_from_db()
        self.assertEqual((self.staff.username, self.staff.get_full_name()), ("jefe", "Juan Pérez"))
        self.assertFalse(Cliente.objects.filter(usuario=self.staff).exists())

    def test_cambiar_contrasena(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse("cambiar_clave"), {
            "old_password": CLAVE, "new_password1": "OtraClave-456", "new_password2": "OtraClave-456",
        })
        self.assertRedirects(resp, reverse("perfil"), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("perfil")).status_code, 200)  # la sesión sigue abierta
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OtraClave-456"))

    def test_cambiar_contrasena_exige_la_actual(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse("cambiar_clave"), {
            "old_password": "incorrecta", "new_password1": "OtraClave-456", "new_password2": "OtraClave-456",
        })
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(CLAVE))

    def test_enlace_en_la_cabecera(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse("catalogo")), reverse("perfil"))
