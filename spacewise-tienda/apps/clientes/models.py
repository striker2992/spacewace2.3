from django.conf import settings
from django.db import models
from django.urls import reverse


class Cliente(models.Model):
    # Cuenta de acceso a la tienda. Es opcional: los clientes cargados a mano por un
    # vendedor (o anteriores a la tienda) no tienen usuario.
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cliente",
    )
    nombre = models.CharField(max_length=150)
    rut = models.CharField("RUT", max_length=20, blank=True)
    razon_social = models.CharField("Empresa / Razón social", max_length=150, blank=True)
    email = models.EmailField("Correo", blank=True)
    telefono = models.CharField("Teléfono", max_length=30, blank=True)
    direccion = models.CharField("Dirección", max_length=255, blank=True)
    informacion_general = models.TextField("Información general", blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("clientes:detalle", args=[self.pk])
