from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Cotizacion(models.Model):
    class Estado(models.TextChoices):
        SOLICITADA = "solicitada", "Solicitada"  # pedida por el cliente, falta valorizarla
        PENDIENTE = "pendiente", "Pendiente"  # valorizada, esperando aprobación
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

    class Origen(models.TextChoices):
        EQUIPO = "equipo", "Equipo de ventas"
        WEB = "web", "Cliente (web)"

    cliente = models.ForeignKey(
        "clientes.Cliente", on_delete=models.PROTECT, related_name="cotizaciones"
    )
    vendedor = models.ForeignKey(
        "vendedores.Vendedor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cotizaciones",
    )
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    fecha = models.DateField(default=timezone.localdate)
    notas = models.TextField(blank=True)
    origen = models.CharField(max_length=10, choices=Origen.choices, default=Origen.EQUIPO)
    fecha_requerida = models.DateField("¿Para cuándo lo necesitas?", null=True, blank=True)
    direccion_entrega = models.CharField("Dirección de entrega", max_length=255, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "cotización"
        verbose_name_plural = "cotizaciones"

    def __str__(self):
        return f"{self.numero} · {self.cliente}"

    @property
    def numero(self):
        return f"COT-{self.pk:04d}" if self.pk else "COT-nueva"

    @property
    def total(self):
        # usa .all() para aprovechar prefetch_related("items", "servicios")
        return sum(item.subtotal for item in self.items.all()) + sum(
            s.subtotal for s in self.servicios.all()
        )

    @property
    def badge(self):
        return {"aprobada": "ok", "pendiente": "warn", "rechazada": "bad", "solicitada": "info"}.get(self.estado, "")

    @property
    def flujo(self):
        """Pasos para el cliente: solicitada -> valorizada -> aprobada/rechazada."""
        orden = [self.Estado.SOLICITADA, self.Estado.PENDIENTE]
        final = self.Estado.RECHAZADA if self.estado == self.Estado.RECHAZADA else self.Estado.APROBADA
        pasos = [(e.value, "Valorizada" if e == self.Estado.PENDIENTE else e.label) for e in orden + [final]]
        actual = [v for v, _ in pasos].index(self.estado)
        return [(v, etiqueta, "done" if i < actual else "current" if i == actual else "") for i, (v, etiqueta) in enumerate(pasos)]

    @property
    def pedido_vigente(self):
        """RQ06: pedido no cancelado creado desde esta cotización (una cotización se compra una vez)."""
        return self.pedidos.exclude(estado=Pedido.Estado.CANCELADO).first()

    def get_absolute_url(self):
        return reverse("cotizaciones:detalle", args=[self.pk])


class CotizacionItem(models.Model):
    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name="items")
    contenedor = models.ForeignKey("contenedores.Contenedor", on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    def __str__(self):
        return f"{self.cantidad} × {self.contenedor.nombre}"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario


class CotizacionServicio(models.Model):
    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name="servicios")
    servicio = models.ForeignKey("contenedores.Servicio", on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    def __str__(self):
        return f"{self.cantidad} × {self.servicio.nombre}"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario


# ---------------------------------------------------------------------------
# Tienda: carrito de compras
# ---------------------------------------------------------------------------
class Carrito(models.Model):
    """Carrito de un usuario autenticado, o anónimo (usuario=None) ligado a la sesión.

    El id del carrito anónimo se guarda en `request.session["carrito_id"]`; al iniciar
    sesión se fusiona con el carrito del usuario (ver carrito.fusionar_carritos).
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="carrito",
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Carrito {self.pk} ({self.usuario or 'anónimo'})"

    @property
    def cantidad_total(self):
        return sum(item.cantidad for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())

    total = subtotal  # sin impuestos ni despacho por ahora: total == subtotal


class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name="items")
    contenedor = models.ForeignKey("contenedores.Contenedor", on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["carrito", "contenedor"], name="item_unico_por_carrito"),
        ]

    def __str__(self):
        return f"{self.cantidad} × {self.contenedor.nombre}"

    @property
    def precio_unitario(self):
        return self.contenedor.precio

    @property
    def subtotal(self):
        return self.cantidad * self.contenedor.precio


# ---------------------------------------------------------------------------
# Tienda: pedidos confirmados
# ---------------------------------------------------------------------------
class Pedido(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_PROCESO = "en_proceso", "En proceso"
        DESPACHADO = "despachado", "Despachado"
        COMPLETADO = "completado", "Completado"
        CANCELADO = "cancelado", "Cancelado"

    class MetodoContacto(models.TextChoices):
        EMAIL = "email", "Correo electrónico"
        TELEFONO = "telefono", "Llamada telefónica"
        WHATSAPP = "whatsapp", "WhatsApp"

    # Transiciones permitidas. COMPLETADO y CANCELADO son finales: cancelar devuelve el
    # stock una sola vez y no se puede reabrir un pedido ya cancelado.
    TRANSICIONES = {
        Estado.PENDIENTE: [Estado.EN_PROCESO, Estado.CANCELADO],
        Estado.EN_PROCESO: [Estado.DESPACHADO, Estado.CANCELADO],
        Estado.DESPACHADO: [Estado.COMPLETADO],
        Estado.COMPLETADO: [],
        Estado.CANCELADO: [],
    }

    cliente = models.ForeignKey(
        "clientes.Cliente", on_delete=models.PROTECT, related_name="pedidos"
    )
    numero_pedido = models.CharField(max_length=20, unique=True, null=True, editable=False)
    # RQ06: si se compró desde una cotización aprobada (los pedidos del carrito no tienen).
    cotizacion = models.ForeignKey(
        Cotizacion, on_delete=models.PROTECT, null=True, blank=True, editable=False, related_name="pedidos"
    )
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    # Datos de entrega y contacto tal como el cliente los confirmó en el checkout
    # (se copian al pedido para que no cambien si luego edita su perfil).
    direccion_entrega = models.CharField("Dirección de entrega", max_length=255)
    telefono_contacto = models.CharField("Teléfono de contacto", max_length=30)
    metodo_contacto = models.CharField(
        "Forma de contacto", max_length=10, choices=MetodoContacto.choices, default=MetodoContacto.EMAIL
    )
    notas = models.TextField("Notas del cliente", blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion", "-id"]

    def __str__(self):
        return f"{self.numero_pedido or 'Pedido nuevo'} · {self.cliente}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.numero_pedido:
            # El código se deriva del id (único por definición), igual que COT-0001.
            self.numero_pedido = f"PED-{self.pk:06d}"
            super().save(update_fields=["numero_pedido"])

    @property
    def badge(self):
        return {
            "pendiente": "warn",
            "en_proceso": "info",
            "despachado": "info",
            "completado": "ok",
            "cancelado": "bad",
        }.get(self.estado, "")

    @property
    def flujo(self):
        """Pasos del avance (pendiente -> completado) con su situación: done / current / ''."""
        pasos = [self.Estado.PENDIENTE, self.Estado.EN_PROCESO, self.Estado.DESPACHADO, self.Estado.COMPLETADO]
        if self.estado == self.Estado.CANCELADO:
            return []
        actual = pasos.index(self.Estado(self.estado))
        return [
            (e.value, e.label, "done" if i < actual else "current" if i == actual else "")
            for i, e in enumerate(pasos)
        ]

    @property
    def estados_siguientes(self):
        return [(e.value, e.label) for e in self.TRANSICIONES[self.Estado(self.estado)]]

    def get_absolute_url(self):
        return reverse("tienda:detalle_pedido", args=[self.pk])


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="items")
    contenedor = models.ForeignKey("contenedores.Contenedor", on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    # Precio al momento de la compra: si el catálogo cambia, el pedido no.
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad} × {self.contenedor.nombre}"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario


class ServicioPedido(models.Model):
    """Servicio adicional de un pedido comprado desde una cotización (transporte, instalación...)."""

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="servicios")
    servicio = models.ForeignKey("contenedores.Servicio", on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad} × {self.servicio.nombre}"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario
