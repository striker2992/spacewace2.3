from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.clientes.models import Cliente
from apps.contenedores.models import Contenedor
from apps.cotizaciones.models import ItemPedido, Pedido

from .models import Garantia
from .servicios import GarantiaError, resolver_garantia, solicitar_garantia

CLAVE = "clave-de-prueba-123"
MOTIVO = "Filtración de agua por el techo"


class GarantiaTests(TestCase):
    """RQ12 / UC-08: el cliente solicita garantía de un pedido y el equipo registra su resolución."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user("ana@ejemplo.cl", email="ana@ejemplo.cl", password=CLAVE)
        cls.otro = User.objects.create_user("beto@ejemplo.cl", email="beto@ejemplo.cl", password=CLAVE)
        cls.staff = User.objects.create_user("jefe", password=CLAVE, is_staff=True)
        cls.cliente = Cliente.objects.create(usuario=cls.user, nombre="Ana Soto", email="ana@ejemplo.cl")
        cls.c20 = Contenedor.objects.create(nombre="Dry 20", tipo="20DC", precio=4000, stock=5)
        cls.c40 = Contenedor.objects.create(nombre="Dry 40", tipo="40DC", precio=6000, stock=5)

    def setUp(self):
        self.pedido = Pedido.objects.create(
            cliente=self.cliente, estado=Pedido.Estado.COMPLETADO, direccion_entrega="Coronel", telefono_contacto="+56911112222",
        )
        self.i20 = ItemPedido.objects.create(pedido=self.pedido, contenedor=self.c20, cantidad=2, precio_unitario=4000)
        self.i40 = ItemPedido.objects.create(pedido=self.pedido, contenedor=self.c40, cantidad=1, precio_unitario=6000)

    def solicitar(self, usuario=None, **datos):
        self.client.force_login(usuario or self.user)
        datos = {"motivo": MOTIVO, f"cantidad_{self.i20.pk}": "1", f"cantidad_{self.i40.pk}": "0", **datos}
        return self.client.post(reverse("garantias:solicitar", args=[self.pedido.pk]), datos)

    def test_cliente_solicita_garantia(self):
        resp = self.solicitar()
        g = Garantia.objects.get()
        self.assertRedirects(resp, reverse("garantias:mi_garantia", args=[g.pk]), fetch_redirect_response=False)
        self.assertEqual((g.pedido, g.estado, g.motivo), (self.pedido, "pendiente", MOTIVO))
        self.assertEqual([(i.contenedor, i.cantidad) for i in g.items.all()], [(self.c20, 1)])

    def test_boton_solo_en_pedidos_despachados_o_completados(self):
        self.client.force_login(self.user)
        url = reverse("garantias:solicitar", args=[self.pedido.pk])
        self.assertContains(self.client.get(self.pedido.get_absolute_url()), url)
        for estado in ("pendiente", "en_proceso", "cancelado"):
            Pedido.objects.filter(pk=self.pedido.pk).update(estado=estado)
            self.assertNotContains(self.client.get(self.pedido.get_absolute_url()), url)
            resp = self.solicitar()
            self.assertRedirects(resp, self.pedido.get_absolute_url(), fetch_redirect_response=False)
        self.assertFalse(Garantia.objects.exists())

    def test_una_solicitud_pendiente_por_pedido(self):
        self.solicitar()
        self.solicitar()
        self.assertEqual(Garantia.objects.count(), 1)
        # Resuelta la anterior, puede pedir otra.
        resolver_garantia(Garantia.objects.get(), "rechazada", "No corresponde a falla de fábrica", self.staff)
        self.solicitar()
        self.assertEqual(Garantia.objects.count(), 2)

    def test_valida_cantidades_y_motivo(self):
        resp = self.solicitar(**{f"cantidad_{self.i20.pk}": "0"})
        self.assertContains(resp, "Indica al menos un contenedor afectado.")
        resp = self.solicitar(**{f"cantidad_{self.i20.pk}": "3"})  # compró 2
        self.assertEqual(resp.status_code, 200)
        resp = self.solicitar(motivo="corto")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Garantia.objects.exists())

    def test_servicio_rechaza_items_de_otro_pedido(self):
        otro = Pedido.objects.create(cliente=self.cliente, estado="completado", direccion_entrega="x", telefono_contacto="1")
        ajeno = ItemPedido.objects.create(pedido=otro, contenedor=self.c20, cantidad=5, precio_unitario=1)
        with self.assertRaises(GarantiaError):
            solicitar_garantia(self.pedido, MOTIVO, [(ajeno, 1)])

    def test_otro_cliente_no_accede(self):
        resp = self.solicitar(usuario=self.otro)
        self.assertEqual(resp.status_code, 404)
        self.solicitar()
        g = Garantia.objects.get()
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(reverse("garantias:mi_garantia", args=[g.pk])).status_code, 404)
        self.assertEqual(list(self.client.get(reverse("garantias:mis_garantias")).context["garantias"]), [])

    def test_equipo_interno_no_solicita_y_cliente_no_entra_al_panel(self):
        resp = self.solicitar(usuario=self.staff)
        self.assertRedirects(resp, reverse("dashboard"), fetch_redirect_response=False)
        self.client.force_login(self.user)
        resp = self.client.get(reverse("garantias:lista"))
        self.assertRedirects(resp, reverse("catalogo"), fetch_redirect_response=False)

    def test_equipo_ve_bandeja_aviso_y_resuelve(self):
        self.solicitar()
        g = Garantia.objects.get()
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(reverse("dashboard")), "garantía por revisar")
        resp = self.client.get(reverse("garantias:lista"), {"estado": "pendiente"})
        self.assertContains(resp, g.numero)
        resp = self.client.post(reverse("garantias:resolver", args=[g.pk]), {
            "estado": "aprobada", "resolucion": "Se coordinará una visita técnica el lunes.",
        })
        self.assertRedirects(resp, g.get_absolute_url(), fetch_redirect_response=False)
        g.refresh_from_db()
        self.assertEqual((g.estado, g.resuelta_por), ("aprobada", self.staff))
        self.assertIsNotNone(g.fecha_resolucion)
        self.assertEqual(mail.outbox[0].to, ["ana@ejemplo.cl"])

        # El cliente ve la resolución.
        self.client.force_login(self.user)
        resp = self.client.get(reverse("garantias:mi_garantia", args=[g.pk]))
        self.assertContains(resp, "visita técnica")

    def test_resolver_exige_texto_y_no_se_resuelve_dos_veces(self):
        self.solicitar()
        g = Garantia.objects.get()
        self.client.force_login(self.staff)
        resp = self.client.post(reverse("garantias:resolver", args=[g.pk]), {"estado": "aprobada", "resolucion": ""})
        self.assertEqual(resp.status_code, 400)
        resolver_garantia(g, "rechazada", "Daño por mal uso del cliente", self.staff)
        with self.assertRaises(GarantiaError):
            resolver_garantia(g, "aprobada", "Cambio de opinión del equipo", self.staff)
        g.refresh_from_db()
        self.assertEqual(g.estado, "rechazada")

    def test_pedido_muestra_sus_garantias(self):
        self.solicitar()
        g = Garantia.objects.get()
        self.assertContains(self.client.get(self.pedido.get_absolute_url()), g.numero)
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(reverse("vendedores:detalle_pedido", args=[self.pedido.pk])), g.numero)
