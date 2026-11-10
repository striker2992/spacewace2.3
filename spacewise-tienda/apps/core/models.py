from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class SeguridadCuenta(models.Model):
    """Intentos fallidos de inicio de sesión y bloqueo temporal de una cuenta."""

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
    def se_desbloquea_en(self):
        """Hora en que termina el bloqueo (None si no está bloqueada)."""
        if self.bloqueada_en is None:
            return None
        return self.bloqueada_en + timedelta(minutes=settings.LOGIN_BLOQUEO_MINUTOS)

    @property
    def bloqueada(self):
        return self.bloqueada_en is not None and self.se_desbloquea_en > timezone.now()
