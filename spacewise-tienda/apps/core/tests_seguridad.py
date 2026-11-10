import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.clientes.models import Cliente

CLAVE = "clave-de-prueba-123"


class BloqueoCuentaTests(TestCase):
    """SEG-12: tras 4 intentos fallidos la cuenta se bloquea 15 minutos (un administrador puede liberarla antes)."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.ana = User.objects.create_user("ana@ejemplo.cl", email="ana@ejemplo.cl", password=CLAVE)
        cls.cliente = Cliente.objects.create(usuario=cls.ana, nombre="Ana Soto", email="ana@ejemplo.cl")
        cls.admin = User.objects.create_user("jefe", password=CLAVE, is_staff=True)
        cls.vendedor_user = User.objects.create_user("vende", password=CLAVE)
        from apps.vendedores.models import Vendedor

        Vendedor.objects.create(user=cls.vendedor_user, codigo="V-1")

    def setUp(self):
        cache.clear()

    def entrar(self, clave, usuario="ana@ejemplo.cl", ip="10.0.0.1"):
        return self.client.post(reverse("login"), {"username": usuario, "password": clave}, REMOTE_ADDR=ip)

    def bloquear(self, usuario="ana@ejemplo.cl"):
        for _ in range(4):
            self.entrar("mala", usuario=usuario)

    def test_cuarto_fallo_bloquea_y_la_clave_correcta_ya_no_sirve(self):
        for _ in range(3):
            self.assertEqual(self.entrar("mala").status_code, 200)
        resp = self.entrar("mala")
        self.assertContains(resp, "Tu cuenta está bloqueada")
        resp = self.entrar(CLAVE, ip="10.9.9.9")  # tampoco desde otra conexión
        self.assertContains(resp, "bloqueada por 15 minutos", status_code=403)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_un_acierto_reinicia_el_contador(self):
        for _ in range(3):
            self.entrar("mala")
        self.assertEqual(self.entrar(CLAVE).status_code, 302)
        self.client.logout()
        for _ in range(3):
            self.entrar("mala")
        self.assertEqual(self.entrar(CLAVE).status_code, 302)

    def test_a_los_15_minutos_se_desbloquea_sola(self):
        from datetime import timedelta

        from django.utils import timezone

        from apps.core.models import SeguridadCuenta

        self.bloquear()
        hace = lambda m: timezone.now() - timedelta(minutes=m)  # noqa: E731
        SeguridadCuenta.objects.filter(usuario=self.ana).update(bloqueada_en=hace(14))
        self.assertEqual(self.entrar(CLAVE).status_code, 403)  # aún faltaba un minuto
        SeguridadCuenta.objects.filter(usuario=self.ana).update(bloqueada_en=hace(16))
        self.assertEqual(self.entrar(CLAVE).status_code, 302)
        self.assertEqual(SeguridadCuenta.objects.get(usuario=self.ana).intentos_fallidos, 0)

    def test_tras_vencer_vuelve_a_tener_4_intentos(self):
        from datetime import timedelta

        from django.utils import timezone

        from apps.core.models import SeguridadCuenta

        self.bloquear()
        SeguridadCuenta.objects.filter(usuario=self.ana).update(bloqueada_en=timezone.now() - timedelta(minutes=16))
        for _ in range(3):
            self.assertEqual(self.entrar("mala").status_code, 200)
        self.assertContains(self.entrar("mala"), "Tu cuenta está bloqueada")

    def test_tambien_con_el_nombre_de_usuario_del_equipo(self):
        self.bloquear(usuario="JEFE")
        self.assertEqual(self.entrar(CLAVE, usuario="jefe").status_code, 403)

    def test_administrador_ve_y_desbloquea_desde_el_panel(self):
        self.bloquear()
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("dashboard")), "1 cuenta bloqueada")
        resp = self.client.get(reverse("cuentas_bloqueadas"))
        self.assertContains(resp, "ana@ejemplo.cl")
        self.assertContains(self.client.get(self.cliente.get_absolute_url()), "Cuenta bloqueada")
        self.client.post(reverse("desbloquear_cuenta", args=[self.ana.pk]))
        self.client.logout()
        self.assertEqual(self.entrar(CLAVE).status_code, 302)
        from apps.core.models import SeguridadCuenta

        seg = SeguridadCuenta.objects.get(usuario=self.ana)
        self.assertEqual((seg.intentos_fallidos, seg.desbloqueada_por), (0, self.admin))

    def test_vendedor_y_cliente_no_desbloquean(self):
        self.bloquear()
        for quien in (self.vendedor_user,):
            self.client.force_login(quien)
            self.assertRedirects(self.client.get(reverse("cuentas_bloqueadas")), reverse("dashboard"), fetch_redirect_response=False)
            self.client.post(reverse("desbloquear_cuenta", args=[self.ana.pk]))
        otro = get_user_model().objects.create_user("beto@ejemplo.cl", email="beto@ejemplo.cl", password=CLAVE)
        self.client.force_login(otro)
        self.client.post(reverse("desbloquear_cuenta", args=[self.ana.pk]))
        from apps.core.cuentas import esta_bloqueada

        self.assertTrue(esta_bloqueada(self.ana))

    def test_comando_para_desbloquear_al_administrador(self):
        from io import StringIO

        from django.core.management import call_command

        from apps.core.cuentas import esta_bloqueada

        self.bloquear(usuario="jefe")
        self.assertTrue(esta_bloqueada(self.admin))
        call_command("desbloquear_cuenta", "jefe", stdout=StringIO())
        self.assertFalse(esta_bloqueada(self.admin))

    def test_recuperar_clave_no_libera_una_cuenta_bloqueada(self):
        self.bloquear()
        resp = self.client.post(reverse("olvide_clave"), {"email": "ana@ejemplo.cl"})
        self.assertRedirects(resp, reverse("clave_enviada"))  # misma respuesta, pero sin correo
        self.assertEqual(len(mail.outbox), 0)

    def test_correo_inexistente_no_crea_registros(self):
        from apps.core.models import SeguridadCuenta

        for _ in range(6):
            self.entrar("mala", usuario="nadie@ejemplo.cl")
        self.assertFalse(SeguridadCuenta.objects.exists())

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


class SeedServiciosTests(TestCase):
    def test_agrega_los_servicios_que_falten_aunque_ya_haya_datos(self):
        from io import StringIO

        from django.core.management import call_command

        from apps.contenedores.models import Contenedor, Servicio

        from .management.commands.seed import SERVICIOS

        # Una base "antigua": con contenedores y solo uno de los servicios.
        Contenedor.objects.create(nombre="Dry 20", tipo="20DC", precio=4000, stock=1)
        Servicio.objects.create(nombre="Transporte y entrega", precio=999, unidad="km")
        call_command("seed", clave_equipo="Equipo-Demo-2026", stdout=StringIO())
        self.assertEqual(Servicio.objects.count(), len(SERVICIOS))
        self.assertEqual(Servicio.objects.get(nombre="Transporte y entrega").precio, 999)  # no pisa lo existente
        self.assertEqual(Contenedor.objects.count(), 1)  # no carga más datos
        call_command("seed", clave_equipo="Equipo-Demo-2026", stdout=StringIO())
        self.assertEqual(Servicio.objects.count(), len(SERVICIOS))  # no duplica


class PreciosChilenosTests(TestCase):
    def test_formato_de_montos(self):
        from django.template import engines
        from django.utils import translation

        t = engines["django"].from_string('{% load ui %}${{ a|floatformat:"0g" }}|{{ a|compact }}|{{ b|compact }}')
        with translation.override("es"):
            self.assertEqual(t.render({"a": 3900000, "b": 15500}), "$3.900.000|$3,9M|$15,5k")

    def test_actualizar_precios_de_una_base_existente(self):
        from io import StringIO

        from django.core.management import call_command

        from apps.contenedores.models import Contenedor, Servicio

        viejo = Contenedor.objects.create(nombre="Contenedor 20' estándar", tipo="20DC", condicion="usado", precio=2600, stock=1)
        propio = Contenedor.objects.create(nombre="Mi contenedor", tipo="20DC", precio=1234, stock=1)
        Servicio.objects.create(nombre="Climatización", precio=5200, unidad="unidad")
        call_command("seed", clave_equipo="x-Equipo-2026", actualizar_precios=True, stdout=StringIO())
        viejo.refresh_from_db()
        propio.refresh_from_db()
        self.assertEqual(viejo.precio, 2100000)
        self.assertEqual(Servicio.objects.get(nombre="Climatización").precio, 520000)
        self.assertEqual(propio.precio, 1234)  # lo que no es de la demo no se toca
