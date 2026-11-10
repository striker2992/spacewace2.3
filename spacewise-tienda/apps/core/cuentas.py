"""Bloqueo de cuentas por intentos fallidos de inicio de sesión.

Tras LOGIN_MAX_INTENTOS fallos seguidos la cuenta queda bloqueada, aunque después se escriba la
contraseña correcta, hasta que un administrador la desbloquee (panel «Cuentas bloqueadas» o
`python manage.py desbloquear_cuenta`). Un inicio de sesión exitoso reinicia el contador.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import SeguridadCuenta


def buscar_usuario(identificador):
    """El usuario al que apunta lo escrito en «Correo»: un correo (clientes) o un nombre de usuario."""
    identificador = (identificador or "").strip()
    if not identificador:
        return None
    User = get_user_model()
    if "@" in identificador:
        coincidencias = list(User.objects.filter(email__iexact=identificador)[:2])
        return coincidencias[0] if len(coincidencias) == 1 else None
    return User.objects.filter(username__iexact=identificador).first()


def esta_bloqueada(usuario):
    return SeguridadCuenta.objects.filter(usuario=usuario, bloqueada_en__isnull=False).exists()


def registrar_fallo(usuario, ip=""):
    """Suma un intento fallido; devuelve True si con este la cuenta quedó bloqueada."""
    with transaction.atomic():
        seg, _ = SeguridadCuenta.objects.select_for_update().get_or_create(usuario=usuario)
        if seg.bloqueada:
            return True
        seg.intentos_fallidos += 1
        seg.ultima_ip = ip[:45]
        if seg.intentos_fallidos >= settings.LOGIN_MAX_INTENTOS:
            seg.bloqueada_en = timezone.now()
        seg.save()
        return seg.bloqueada


def registrar_exito(usuario):
    SeguridadCuenta.objects.filter(usuario=usuario, bloqueada_en__isnull=True).update(intentos_fallidos=0)


def desbloquear(usuario, por=None):
    """Libera la cuenta y reinicia el contador. Devuelve False si no estaba bloqueada."""
    return bool(SeguridadCuenta.objects.filter(usuario=usuario, bloqueada_en__isnull=False).update(
        bloqueada_en=None, intentos_fallidos=0, desbloqueada_en=timezone.now(), desbloqueada_por=por,
    ))


def cuentas_bloqueadas():
    return SeguridadCuenta.objects.filter(bloqueada_en__isnull=False).select_related("usuario__cliente")
