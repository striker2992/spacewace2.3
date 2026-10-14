from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Cliente

DATOS = {
    "username": "nuevo", "first_name": "Ana", "last_name": "Soto", "email": "ana@ejemplo.cl",
    "rut": "12.345.678-5", "telefono": "+56 9 1111 2222", "razon_social": "Soto SpA",
    "direccion": "Av. Siempre Viva 123", "password1": "una-clave-muy-larga-987", "password2": "una-clave-muy-larga-987",
}


class RegistroTests(TestCase):
    def test_crea_usuario_y_perfil_de_cliente_e_inicia_sesion(self):
        resp = self.client.post(reverse("registro"), DATOS)
        self.assertRedirects(resp, reverse("catalogo"), fetch_redirect_response=False)
        user = get_user_model().objects.get(username="nuevo")
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
