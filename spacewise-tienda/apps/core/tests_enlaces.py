"""UX-03: recorre la aplicación con cada rol siguiendo todos los enlaces internos y verifica
que ninguno esté roto (404) ni falle (500). Usa los datos de demostración de `seed`."""

import re
from collections import deque
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.cotizaciones.models import Cotizacion

ENLACE = re.compile(r'href="(/[^"#]*)"')
NO_SEGUIR = ("/accounts/logout/", "/admin/", "/static/", "/media/")


class EnlacesRotosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Los tests corren con DEBUG=False: seed exige la clave del equipo como en producción.
        call_command("seed", clave_equipo="admin1234", stdout=StringIO())

    def recorrer(self, inicio, limite=400):
        vistos, pendientes, rotos = set(), deque(inicio), []
        while pendientes and len(vistos) < limite:
            url = pendientes.popleft().replace("&amp;", "&")
            if url in vistos or url.startswith(NO_SEGUIR):
                continue
            vistos.add(url)
            resp = self.client.get(url)
            if resp.status_code >= 400:
                rotos.append(f"{url} -> {resp.status_code}")
            elif resp.status_code in (301, 302):
                pendientes.append(resp["Location"])
            elif "text/html" in resp.get("Content-Type", ""):
                pendientes.extend(ENLACE.findall(resp.content.decode()))
        return vistos, rotos

    def test_visitante(self):
        cot = Cotizacion.objects.first()
        vistos, rotos = self.recorrer(["/", "/catalogo/", "/accounts/login/", "/accounts/registro/", f"/c/{cot.token}/"])
        self.assertEqual(rotos, [])
        self.assertGreater(len(vistos), 10)

    def test_cliente(self):
        self.assertTrue(self.client.login(username="camila@ejemplo.cl", password="demo1234"))
        vistos, rotos = self.recorrer(["/", "/cotizaciones/", "/pedidos/", "/garantias/", "/accounts/perfil/"])
        self.assertEqual(rotos, [])
        self.assertGreater(len(vistos), 10)

    def test_equipo(self):
        self.assertTrue(self.client.login(username="admin", password="admin1234"))
        vistos, rotos = self.recorrer(["/panel/", "/panel/reportes/"])
        self.assertEqual(rotos, [])
        self.assertGreater(len(vistos), 30)
