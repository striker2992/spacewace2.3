from django.conf import settings
from django.db import models


class Vendedor(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vendedor_profile",
    )
    codigo = models.CharField(max_length=20, unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"Vendedor: {self.user.get_full_name() or self.user.username}"