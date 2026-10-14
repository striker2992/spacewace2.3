from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .carrito import fusionar_carritos


@receiver(user_logged_in)
def fusionar_carrito_al_iniciar_sesion(sender, request, user, **kwargs):
    if request is not None:  # p. ej. `manage.py` o tests sin request
        fusionar_carritos(request, user)
