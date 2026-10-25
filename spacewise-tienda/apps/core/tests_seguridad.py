import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.clientes.models import Cliente

CLAVE = "clave-de-prueba-123"


class LimiteIntentosTests(TestCase):
    """SEG-12: tras varios intentos fallidos se bloquea el inicio de sesión por un tiempo."""

    @classmethod
    def setUpTestData(cls):
        get_user_model().objects.create_user("ana@ejemplo.cl", email="ana@ejemplo.cl", password=CLAVE)

    def setUp(self):
        cache.clear()

    def entrar(self, clave, usuario="ana@ejemplo.cl", ip="10.0.0.1"):
        return self.client.post(reverse("login"), {"username": usuario, "password": clave}, REMOTE_ADDR=ip)

    @override_settings(LOGIN_MAX_INTENTOS=3)
    def test_bloquea_tras_los_intentos_fallidos_aunque_la_clave_sea_correcta(self):
        for _ in range(3):
            self.assertEqual(self.entrar("mala").status_code, 200)
        resp = self.entrar(CLAVE)
        self.assertEqual(resp.status_code, 429)
        self.assertContains(resp, "Demasiados intentos fallidos", status_code=429)
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(LOGIN_MAX_INTENTOS=3)
    def test_el_bloqueo_es_por_ip_y_un_acierto_reinicia_el_contador(self):
        for _ in range(3):
            self.entrar("mala")
        self.assertEqual(self.entrar(CLAVE, ip="10.0.0.2").status_code, 302)  # otra IP sí entra
        self.client.logout()
        cache.clear()
        self.entrar("mala")
        self.entrar("mala")
        self.assertEqual(self.entrar(CLAVE).status_code, 302)
        self.client.logout()
        self.entrar("mala")
        self.entrar("mala")
        self.assertEqual(self.entrar(CLAVE).status_code, 302)  # el contador se había reiniciado

    @override_settings(LOGIN_MAX_INTENTOS_IP=4)
    def test_limite_por_ip_probando_muchas_cuentas(self):
        for i in range(4):
            self.entrar("mala", usuario=f"x{i}@ejemplo.cl")
        self.assertEqual(self.entrar(CLAVE).status_code, 429)

    def test_login_del_admin_pasa_por_el_login_con_limite(self):
        resp = self.client.get("/admin/login/")
        self.assertRedirects(resp, "/accounts/login/?next=/admin/", fetch_redirect_response=False)


class RecuperarClaveTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("ana@ejemplo.cl", email="ana@ejemplo.cl", password=CLAVE)

    def setUp(self):
        cache.clear()

    def test_flujo_completo(self):
        self.assertContains(self.client.get(reverse("login")), reverse("olvide_clave"))
        resp = self.client.post(reverse("olvide_clave"), {"email": "ANA@ejemplo.cl"})
        self.assertRedirects(resp, reverse("clave_enviada"))
        self.assertEqual(len(mail.outbox), 1)
        enlace = re.search(r"https?://[^/]+(/accounts/clave/restablecer/\S+)", mail.outbox[0].body)[1]
        resp = self.client.get(enlace, follow=True)  # Django cambia el token de la URL por uno de sesión
        self.assertContains(resp, "Elige una contraseña nueva")
        resp = self.client.post(resp.redirect_chain[-1][0], {"new_password1": "Nueva-Clave-789", "new_password2": "Nueva-Clave-789"})
        self.assertRedirects(resp, reverse("clave_lista"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Nueva-Clave-789"))
        # El enlace sirve una sola vez.
        self.assertContains(self.client.get(enlace, follow=True), "Enlace no válido")

    def test_misma_respuesta_si_el_correo_no_existe(self):
        resp = self.client.post(reverse("olvide_clave"), {"email": "nadie@ejemplo.cl"})
        self.assertRedirects(resp, reverse("clave_enviada"))
        self.assertEqual(len(mail.outbox), 0)

    def test_maximo_de_solicitudes_por_hora(self):
        for _ in range(8):
            self.client.post(reverse("olvide_clave"), {"email": "ana@ejemplo.cl"})
        self.assertEqual(len(mail.outbox), 5)


class FichaSinAccesoTests(TestCase):
    """EDGE-20: registrarse con el correo de una ficha creada por el equipo no duplica ni toma la ficha."""

    @classmethod
    def setUpTestData(cls):
        cls.ficha = Cliente.objects.create(nombre="Constructora Sur", email="compras@sur.cl")

    def test_registro_bloqueado_con_mensaje(self):
        resp = self.client.post(reverse("registro"), {
            "email": "Compras@Sur.cl", "first_name": "Ana", "last_name": "Soto", "rut": "12.345.678-5",
            "telefono": "+56911112222", "password1": "Clave-Segura-456", "password2": "Clave-Segura-456",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Ya tenemos una ficha de cliente con este correo")
        self.assertEqual(Cliente.objects.count(), 1)
        self.assertFalse(get_user_model().objects.filter(email__iexact="compras@sur.cl").exists())

    def test_el_equipo_le_da_acceso_desde_la_ficha(self):
        staff = get_user_model().objects.create_user("jefe", password=CLAVE, is_staff=True)
        self.client.force_login(staff)
        self.client.post(reverse("clientes:editar", args=[self.ficha.pk]), {
            "nombre": "Constructora Sur", "email": "compras@sur.cl", "password1": "Clave-Segura-456",
            "password2": "Clave-Segura-456",
        })
        self.ficha.refresh_from_db()
        self.assertIsNotNone(self.ficha.usuario)
        self.client.logout()
        self.assertTrue(self.client.login(username="compras@sur.cl", password="Clave-Segura-456"))


class ConfiguracionTests(TestCase):
    def test_sesion_por_inactividad(self):
        from django.conf import settings

        self.assertEqual(settings.SESSION_COOKIE_AGE, 8 * 3600)
        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
    def test_pagina_404_propia(self):
        resp = self.client.get("/no-existe/")
        self.assertContains(resp, "No encontramos esta página", status_code=404)


class DespliegueTests(TestCase):
    """Detrás del proxy de un hosting, la IP del visitante se toma de X-Forwarded-For."""

    def setUp(self):
        from django.test import RequestFactory

        self.rf = RequestFactory()

    def ip(self, xff="", remota="10.0.0.1"):
        from apps.core.views import ip_cliente

        meta = {"REMOTE_ADDR": remota}
        if xff:
            meta["HTTP_X_FORWARDED_FOR"] = xff
        return ip_cliente(self.rf.get("/", **meta))

    def test_sin_proxy_usa_remote_addr_e_ignora_cabeceras_inventadas(self):
        self.assertEqual(self.ip("1.2.3.4"), "10.0.0.1")

    @override_settings(PROXY_SALTOS=1)
    def test_con_un_proxy_usa_la_ip_que_agrego_el_proxy(self):
        # El cliente puede inventar la primera; la última la agrega el proxy del hosting.
        self.assertEqual(self.ip("6.6.6.6, 203.0.113.7"), "203.0.113.7")
        self.assertEqual(self.ip(""), "10.0.0.1")

    @override_settings(IP_CABECERA="X-Real-IP")
    def test_cabecera_del_hosting(self):
        from apps.core.views import ip_cliente

        req = self.rf.get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_REAL_IP="203.0.113.9", HTTP_X_FORWARDED_FOR="6.6.6.6")
        self.assertEqual(ip_cliente(req), "203.0.113.9")
        self.assertEqual(self.ip(), "10.0.0.1")  # sin la cabecera, la conexión

    def test_seed_en_produccion_exige_clave_del_equipo(self):
        from io import StringIO

        from django.core.management import call_command
        from django.core.management.base import CommandError

        with override_settings(DEBUG=False):
            with self.assertRaises(CommandError):
                call_command("seed", stdout=StringIO())
            call_command("seed", clave_equipo="Equipo-Demo-2026", stdout=StringIO())
        User = get_user_model()
        self.assertTrue(User.objects.get(username="admin").check_password("Equipo-Demo-2026"))
        self.assertTrue(User.objects.get(username="ana").check_password("Equipo-Demo-2026"))
