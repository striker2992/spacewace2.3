from django.core.management.base import BaseCommand, CommandError

from apps.core.cuentas import buscar_usuario, desbloquear


class Command(BaseCommand):
    help = "Desbloquea una cuenta bloqueada por intentos fallidos (útil si se bloqueó la del administrador)."

    def add_arguments(self, parser):
        parser.add_argument("usuario", help="Nombre de usuario o correo de la cuenta")

    def handle(self, *args, **options):
        usuario = buscar_usuario(options["usuario"])
        if usuario is None:
            raise CommandError(f"No existe la cuenta «{options['usuario']}».")
        if desbloquear(usuario):
            self.stdout.write(self.style.SUCCESS(f"Cuenta «{usuario.username}» desbloqueada."))
        else:
            self.stdout.write(f"La cuenta «{usuario.username}» no estaba bloqueada.")
