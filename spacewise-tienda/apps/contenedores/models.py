from django.db import models
from django.urls import reverse


class Contenedor(models.Model):
    class Tipo(models.TextChoices):
        DRY_20 = "20DC", "20' Dry"
        DRY_40 = "40DC", "40' Dry"
        HC_40 = "40HC", "40' High Cube"
        REEFER_40 = "40RF", "40' Refrigerado"
        OPEN_TOP_20 = "20OT", "20' Open Top"

    class Condicion(models.TextChoices):
        NUEVO = "nuevo", "Nuevo"
        USADO = "usado", "Usado"

    nombre = models.CharField(max_length=120)
    tipo = models.CharField(max_length=4, choices=Tipo.choices)
    condicion = models.CharField(max_length=10, choices=Condicion.choices, default=Condicion.NUEVO)
    precio = models.DecimalField("Precio unitario", max_digits=12, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    ubicacion = models.CharField("Ubicación", max_length=120, blank=True)
    descripcion = models.TextField("Descripción", blank=True)
    especificaciones = models.TextField(
        "Especificaciones técnicas",
        blank=True,
        help_text="Una por línea. Ej.: Medidas internas: 5,90 x 2,35 x 2,39 m",
    )
    imagen = models.ImageField("Imagen", upload_to="contenedores/", blank=True)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name_plural = "contenedores"

    def __str__(self):
        return f"{self.nombre} ({self.get_condicion_display()})"

    def get_absolute_url(self):
        return reverse("detalle_contenedor", args=[self.pk])

    @property
    def disponible(self):
        return self.activo and self.stock > 0

    @property
    def lista_especificaciones(self):
        return [linea.strip() for linea in self.especificaciones.splitlines() if linea.strip()]
