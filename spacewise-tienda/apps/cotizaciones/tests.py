from django.contrib.auth import get_user_model
from django.contrib.admin.sites import site as admin_site
from django.test import TestCase
from django.urls import reverse

from apps.clientes.models import Cliente
from apps.contenedores.models import Contenedor
from apps.vendedores.models import Vendedor

from .models import Carrito, ItemCarrito, ItemPedido, Pedido
from .servicios import PedidoError, cambiar_estado_pedido

CLAVE = "clave-de-prueba-123"
DATOS_CHECKOUT = {
    "nombre": "Ana Soto", "rut": "12.345.678-5", "razon_social": "Soto SpA",
    "direccion_entrega": "Av. Siempre Viva 123, Coronel", "telefono_contacto": "+56 9 1111 2222",
    "metodo_contacto": "whatsapp", "notas": "Entrega por la mañana",
}


class BaseTienda(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user("ana", email="ana@ejemplo.cl", password=CLAVE)
        cls.otro = User.objects.create_user("beto", password=CLAVE)
        cls.staff = User.objects.create_user("jefe", password=CLAVE, is_staff=True)
        cls.c20 = Contenedor.objects.create(nombre="Veinte", tipo="20DC", precio=4000, stock=5)
        cls.c40 = Contenedor.objects.create(nombre="Cuarenta", tipo="40DC", precio=6000, stock=2)
        cls.sin_stock = Contenedor.objects.create(nombre="Agotado", tipo="20DC", precio=1000, stock=0)

    def agregar(self, contenedor, cantidad=1):
        return self.client.post(reverse("tienda:agregar", args=[contenedor.pk]), {"cantidad": cantidad})

    def hacer_pedido(self, usuario=None):
        self.client.force_login(usuario or self.user)
        self.agregar(self.c20, 2)
        self.agregar(self.c40, 1)
        return self.client.post(reverse("tienda:checkout"), DATOS_CHECKOUT)


class CarritoTests(BaseTienda):
    def test_anonimo_agrega_y_se_guarda_en_sesion(self):
        resp = self.agregar(self.c20, 2)
        self.assertRedirects(resp, reverse("tienda:carrito"))
        carrito = Carrito.objects.get()
        self.assertIsNone(carrito.usuario)
        self.assertEqual(self.client.session["carrito_id"], carrito.pk)
        self.assertEqual(carrito.cantidad_total, 2)

    def test_agregar_dos_veces_suma_cantidad(self):
        self.agregar(self.c20, 1)
        self.agregar(self.c20, 2)
        self.assertEqual(ItemCarrito.objects.get().cantidad, 3)

    def test_no_supera_el_stock(self):
        self.agregar(self.c40, 5)
        self.assertEqual(ItemCarrito.objects.get().cantidad, 2)

    def test_no_agrega_sin_stock_ni_inactivos(self):
        self.agregar(self.sin_stock)
        inactivo = Contenedor.objects.create(nombre="Off", tipo="20DC", precio=1, stock=3, activo=False)
        self.assertEqual(self.agregar(inactivo).status_code, 404)
        self.assertFalse(ItemCarrito.objects.exists())

    def test_agregar_requiere_post(self):
        self.assertEqual(self.client.get(reverse("tienda:agregar", args=[self.c20.pk])).status_code, 405)

    def test_actualizar_y_eliminar(self):
        self.agregar(self.c20, 1)
        item = ItemCarrito.objects.get()
        self.client.post(reverse("tienda:actualizar", args=[item.pk]), {"cantidad": 4})
        item.refresh_from_db()
        self.assertEqual(item.cantidad, 4)
        self.client.post(reverse("tienda:actualizar", args=[item.pk]), {"cantidad": 99})  # tope: stock 5
        item.refresh_from_db()
        self.assertEqual(item.cantidad, 5)
        self.client.post(reverse("tienda:eliminar_item", args=[item.pk]))
        self.assertFalse(ItemCarrito.objects.exists())

    def test_cantidad_cero_elimina(self):
        self.agregar(self.c20, 1)
        item = ItemCarrito.objects.get()
        self.client.post(reverse("tienda:actualizar", args=[item.pk]), {"cantidad": 0})
        self.assertFalse(ItemCarrito.objects.exists())

    def test_cantidad_basura_no_rompe(self):
        self.agregar(self.c20, 1)
        item = ItemCarrito.objects.get()
        resp = self.client.post(reverse("tienda:actualizar", args=[item.pk]), {"cantidad": "abc"})
        self.assertEqual(resp.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.cantidad, 1)

    def test_no_se_puede_tocar_el_carrito_de_otro(self):
        self.client.force_login(self.otro)
        self.agregar(self.c20, 1)
        item_ajeno = ItemCarrito.objects.get()
        self.client.logout()
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(reverse("tienda:eliminar_item", args=[item_ajeno.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("tienda:actualizar", args=[item_ajeno.pk]), {"cantidad": 3}).status_code, 404)
        self.assertTrue(ItemCarrito.objects.filter(pk=item_ajeno.pk).exists())

    def test_totales_dinamicos(self):
        self.agregar(self.c20, 2)
        self.agregar(self.c40, 1)
        resp = self.client.get(reverse("tienda:carrito"))
        self.assertEqual(resp.context["subtotal"], 2 * 4000 + 6000)
        self.assertEqual(resp.context["total"], 14000)

    def test_carrito_anonimo_se_fusiona_al_iniciar_sesion(self):
        self.agregar(self.c20, 2)
        anonimo_id = self.client.session["carrito_id"]
        self.client.login(username="ana", password=CLAVE)
        carrito = Carrito.objects.get(usuario=self.user)
        self.assertEqual(carrito.cantidad_total, 2)
        self.assertFalse(Carrito.objects.filter(pk=anonimo_id).exists())
        self.assertNotIn("carrito_id", self.client.session)

    def test_fusion_suma_con_el_carrito_existente_del_usuario(self):
        existente = Carrito.objects.create(usuario=self.user)
        ItemCarrito.objects.create(carrito=existente, contenedor=self.c20, cantidad=1)
        self.agregar(self.c20, 2)
        self.agregar(self.c40, 1)
        self.client.login(username="ana", password=CLAVE)
        cantidades = {i.contenedor_id: i.cantidad for i in existente.items.all()}
        self.assertEqual(cantidades, {self.c20.pk: 3, self.c40.pk: 1})


class CheckoutTests(BaseTienda):
    def test_sin_sesion_redirige_a_login_con_next(self):
        self.agregar(self.c20)
        resp = self.client.get(reverse("tienda:checkout"))
        self.assertRedirects(
            resp, "/accounts/login/?next=/carrito/checkout/", fetch_redirect_response=False
        )

    def test_tras_login_vuelve_al_checkout_y_conserva_el_carrito(self):
        self.agregar(self.c20, 2)
        resp = self.client.post(
            "/accounts/login/?next=/carrito/checkout/", {"username": "ana", "password": CLAVE}
        )
        self.assertRedirects(resp, "/carrito/checkout/", fetch_redirect_response=False)
        resp = self.client.get("/carrito/checkout/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["total"], 8000)

    def test_checkout_con_carrito_vacio_redirige(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("tienda:checkout"))
        self.assertRedirects(resp, reverse("catalogo"), fetch_redirect_response=False)

    def test_confirmar_crea_pedido_items_y_descuenta_stock(self):
        resp = self.hacer_pedido()
        pedido = Pedido.objects.get()
        self.assertRedirects(resp, reverse("tienda:confirmacion", args=[pedido.pk]))
        self.assertEqual(pedido.numero_pedido, f"PED-{pedido.pk:06d}")
        self.assertEqual(pedido.estado, Pedido.Estado.PENDIENTE)
        self.assertEqual(pedido.total, 2 * 4000 + 6000)
        self.assertEqual(pedido.metodo_contacto, "whatsapp")
        self.assertEqual(pedido.direccion_entrega, DATOS_CHECKOUT["direccion_entrega"])
        self.assertEqual(
            {(i.contenedor_id, i.cantidad, int(i.precio_unitario)) for i in pedido.items.all()},
            {(self.c20.pk, 2, 4000), (self.c40.pk, 1, 6000)},
        )
        self.c20.refresh_from_db(); self.c40.refresh_from_db()
        self.assertEqual((self.c20.stock, self.c40.stock), (3, 1))
        self.assertFalse(ItemCarrito.objects.exists())

    def test_crea_o_actualiza_el_perfil_del_cliente(self):
        self.hacer_pedido()
        cliente = Cliente.objects.get(usuario=self.user)
        self.assertEqual((cliente.rut, cliente.razon_social), ("12.345.678-5", "Soto SpA"))
        self.assertEqual(Pedido.objects.get().cliente, cliente)

    def test_precio_del_pedido_no_cambia_si_cambia_el_catalogo(self):
        self.hacer_pedido()
        Contenedor.objects.filter(pk=self.c20.pk).update(precio=9999)
        item = ItemPedido.objects.get(contenedor=self.c20)
        self.assertEqual(int(item.precio_unitario), 4000)

    def test_stock_cambia_entre_carrito_y_checkout(self):
        self.client.force_login(self.user)
        self.agregar(self.c20, 4)
        Contenedor.objects.filter(pk=self.c20.pk).update(stock=1)  # otro cliente compró
        resp = self.client.post(reverse("tienda:checkout"), DATOS_CHECKOUT)
        self.assertRedirects(resp, reverse("tienda:carrito"), fetch_redirect_response=False)
        self.assertFalse(Pedido.objects.exists())
        self.c20.refresh_from_db()
        self.assertEqual(self.c20.stock, 1)  # nada se descontó
        self.assertTrue(ItemCarrito.objects.exists())  # el carrito se conserva

    def test_datos_invalidos_no_crean_pedido(self):
        self.client.force_login(self.user)
        self.agregar(self.c20)
        resp = self.client.post(reverse("tienda:checkout"), {**DATOS_CHECKOUT, "direccion_entrega": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Pedido.objects.exists())

    def test_confirmar_dos_veces_no_duplica(self):
        self.hacer_pedido()
        resp = self.client.post(reverse("tienda:checkout"), DATOS_CHECKOUT)  # carrito ya vacío
        self.assertRedirects(resp, reverse("catalogo"), fetch_redirect_response=False)
        self.assertEqual(Pedido.objects.count(), 1)


class MisPedidosTests(BaseTienda):
    def test_cada_cliente_ve_solo_sus_pedidos(self):
        self.hacer_pedido(self.user)
        pedido = Pedido.objects.get()
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(reverse("tienda:mis_pedidos")).context["pedidos"].count(), 0)
        self.assertEqual(self.client.get(pedido.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(reverse("tienda:confirmacion", args=[pedido.pk])).status_code, 404)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(pedido.get_absolute_url()).status_code, 200)
        self.assertContains(self.client.get(reverse("tienda:mis_pedidos")), pedido.numero_pedido)

    def test_requiere_login(self):
        resp = self.client.get(reverse("tienda:mis_pedidos"))
        self.assertEqual(resp.status_code, 302)


class GestionPedidosTests(BaseTienda):
    def setUp(self):
        self.hacer_pedido(self.user)
        self.pedido = Pedido.objects.get()
        self.client.logout()

    def test_servicio_cancelar_devuelve_stock_una_sola_vez(self):
        cambiar_estado_pedido(self.pedido, "cancelado")
        self.c20.refresh_from_db(); self.c40.refresh_from_db()
        self.assertEqual((self.c20.stock, self.c40.stock), (5, 2))
        with self.assertRaises(PedidoError):
            cambiar_estado_pedido(self.pedido, "cancelado")
        self.c20.refresh_from_db()
        self.assertEqual(self.c20.stock, 5)

    def test_servicio_rechaza_transiciones_invalidas(self):
        with self.assertRaises(PedidoError):
            cambiar_estado_pedido(self.pedido, "completado")  # pendiente -> completado no existe
        cambiar_estado_pedido(self.pedido, "en_proceso")
        cambiar_estado_pedido(self.pedido, "despachado")
        with self.assertRaises(PedidoError):
            cambiar_estado_pedido(self.pedido, "cancelado")  # ya despachado
        cambiar_estado_pedido(self.pedido, "completado")
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, "completado")

    def test_panel_lista_filtra_por_estado_y_fecha(self):
        self.client.force_login(self.staff)
        url = reverse("vendedores:pedidos")
        self.assertContains(self.client.get(url), self.pedido.numero_pedido)
        self.assertContains(self.client.get(url, {"estado": "pendiente"}), self.pedido.numero_pedido)
        self.assertNotContains(self.client.get(url, {"estado": "completado"}), self.pedido.numero_pedido)
        self.assertNotContains(self.client.get(url, {"desde": "2999-01-01"}), self.pedido.numero_pedido)
        self.assertEqual(self.client.get(url, {"desde": "no-es-fecha"}).status_code, 200)

    def test_vendedor_cambia_estado_desde_el_panel(self):
        vendedor = get_user_model().objects.create_user("vende", password=CLAVE)
        Vendedor.objects.create(user=vendedor)
        self.client.force_login(vendedor)
        resp = self.client.post(reverse("vendedores:pedido_estado", args=[self.pedido.pk]), {"estado": "en_proceso"})
        self.assertRedirects(resp, reverse("vendedores:detalle_pedido", args=[self.pedido.pk]))
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, "en_proceso")

    def test_cambio_invalido_muestra_error_y_no_cambia(self):
        self.client.force_login(self.staff)
        self.client.post(reverse("vendedores:pedido_estado", args=[self.pedido.pk]), {"estado": "completado"})
        self.client.post(reverse("vendedores:pedido_estado", args=[self.pedido.pk]), {"estado": "inventado"})
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, "pendiente")

    def test_cliente_no_accede_al_panel_ni_cambia_estados(self):
        self.client.force_login(self.user)
        for url in (reverse("vendedores:pedidos"), reverse("vendedores:detalle_pedido", args=[self.pedido.pk])):
            self.assertRedirects(self.client.get(url), reverse("catalogo"), fetch_redirect_response=False)
        self.client.post(reverse("vendedores:pedido_estado", args=[self.pedido.pk]), {"estado": "cancelado"})
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, "pendiente")

    def test_pedido_registrado_en_django_admin_con_filtros(self):
        modelo_admin = admin_site._registry[Pedido]
        self.assertIn("estado", modelo_admin.list_filter)
        self.assertIn("fecha_creacion", modelo_admin.list_filter)
        admin_user = get_user_model().objects.create_superuser("root", "r@x.cl", CLAVE)
        self.client.force_login(admin_user)
        self.assertContains(self.client.get(reverse("admin:cotizaciones_pedido_changelist")), self.pedido.numero_pedido)

    def test_admin_cambio_de_estado_devuelve_stock(self):
        admin_user = get_user_model().objects.create_superuser("root", "r@x.cl", CLAVE)
        self.client.force_login(admin_user)
        url = reverse("admin:cotizaciones_pedido_changelist")
        self.client.post(url, {"action": "marcar_cancelado", "_selected_action": [self.pedido.pk]})
        self.pedido.refresh_from_db(); self.c20.refresh_from_db()
        self.assertEqual((self.pedido.estado, self.c20.stock), ("cancelado", 5))
