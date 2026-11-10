from django.conf import settings
from django.db import models


class SeguridadCuenta(models.Model):
    """Intentos fallidos de inicio de sesión y bloqueo de una cuenta (lo libera un administrador)."""

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seguridad")
    intentos_fallidos = models.PositiveSmallIntegerField(default=0)
    bloqueada_en = models.DateTimeField(null=True, blank=True)
    ultima_ip = models.CharField("Última IP de un intento fallido", max_length=45, blank=True)
    desbloqueada_en = models.DateTimeField(null=True, blank=True)
    desbloqueada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "seguridad de cuenta"
        verbose_name_plural = "seguridad de cuentas"

    def __str__(self):
        return f"{self.usuario} ({'bloqueada' if self.bloqueada else 'activa'})"

    @property
    def bloqueada(self):
        return self.bloqueada_en is not None
