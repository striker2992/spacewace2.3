"""Postventa: garantías de los pedidos (RQ12 / UC-08)."""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class Garantia(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

    pedido = models.ForeignKey("cotizaciones.Pedido", on_delete=models.PROTECT, related_name="garantias")
    motivo = models.TextField("Motivo", max_length=1000)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    resolucion = models.TextField("Resolución", max_length=1000, blank=True)
    resuelta_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="garantias_resueltas",
    )
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha_solicitud", "-id"]
        verbose_name = "garantía"
        verbose_name_plural = "garantías"

    def __str__(self):
        return f"{self.numero} · {self.pedido.numero_pedido}"

    @property
    def numero(self):
        return f"GAR-{self.pk:04d}" if self.pk else "GAR-nueva"

    @property
    def badge(self):
        return {"pendiente": "warn", "aprobada": "ok", "rechazada": "bad"}.get(self.estado, "")

    def get_absolute_url(self):
        return reverse("garantias:detalle", args=[self.pk])


class DetalleGarantia(models.Model):
    """Contenedores del pedido afectados por la garantía."""

    garantia = models.ForeignKey(Garantia, on_delete=models.CASCADE, related_name="items")
    contenedor = models.ForeignKey("contenedores.Contenedor", on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    def __str__(self):
        return f"{self.cantidad} × {self.contenedor.nombre}"
