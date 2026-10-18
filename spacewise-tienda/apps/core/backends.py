from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class CorreoOUsuarioBackend(ModelBackend):
    """Permite iniciar sesión con el correo (clientes) o con el nombre de usuario (equipo interno)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username and "@" in username:
            User = get_user_model()
            # Solo si el correo identifica a una única cuenta; si no, no se adivina cuál es.
            coincidencias = list(User.objects.filter(email__iexact=username.strip())[:2])
            if len(coincidencias) != 1:
                User().set_password(password)  # mismo costo que un intento normal (evita sondear correos)
                return None
            username = getattr(coincidencias[0], User.USERNAME_FIELD)
        return super().authenticate(request, username=username, password=password, **kwargs)
