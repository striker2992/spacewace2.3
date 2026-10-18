from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class Contenedor(models.Model):
    class Tipo(models.TextChoices):
        DRY_20 = "20DC", "20' Dry"
        DRY_40 = "40DC", "40' Dry"
        HC_40 = "40HC", "40' High Cube"
        REEFER_40 = "40RF", "40' Refrigerado"
        OPEN_TOP_20 = "20OT", "20' Open Top"
        OFICINA_20 = "20OF", "20' Oficina"
        OFICINA_40 = "40OF", "40' Oficina"

    class Condicion(models.TextChoices):
        NUEVO = "nuevo", "Nuevo"
        USADO = "usado", "Usado"

    class Estado(models.TextChoices):
        DISPONIBLE = "disponible", "Disponible"
        ARRENDADO = "arrendado", "Arrendado"
        MANTENIMIENTO = "mantenimiento", "En mantenimiento"

    nombre = models.CharField(max_length=120)
    tipo = models.CharField(max_length=4, choices=Tipo.choices)
    condicion = models.CharField("Condición", max_length=10, choices=Condicion.choices, default=Condicion.NUEVO)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.DISPONIBLE)
    precio = models.DecimalField(
        "Precio unitario", max_digits=12, decimal_places=2, validators=[MinValueValidator(1)]
    )
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
        """Se puede vender: visible, con stock y no arrendado ni en mantenimiento."""
        return self.activo and self.stock > 0 and self.estado == self.Estado.DISPONIBLE

    @property
    def badge_estado(self):
        return {"disponible": "ok", "arrendado": "info", "mantenimiento": "warn"}.get(self.estado, "")

    @property
    def lista_especificaciones(self):
        return [linea.strip() for linea in self.especificaciones.splitlines() if linea.strip()]


class Servicio(models.Model):
    """Servicio adicional que se ofrece junto a los contenedores (transporte, instalación, etc.)."""

    nombre = models.CharField(max_length=120)
    descripcion = models.TextField("Descripción", blank=True)
    precio = models.DecimalField(
        "Precio referencial", max_digits=12, decimal_places=2, validators=[MinValueValidator(1)]
    )
    unidad = models.CharField(
        "Se cobra por", max_length=40, default="servicio", help_text="Ej.: servicio, km, día, unidad"
    )
    activo = models.BooleanField("Visible en el catálogo", default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name_plural = "servicios"

    def __str__(self):
        return self.nombre
