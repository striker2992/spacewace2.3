"""Publica SpaceWise desde este PC con un túnel de Cloudflare (gratis, sin cuenta).

Uso (dentro de spacewise-tienda, con el venv activado):  python demo_publica.py
o doble clic en demo_publica.bat. Ctrl+C lo apaga todo.

La configuración de la demo se aplica solo mientras corre este script: el .env de
desarrollo no se modifica. Requiere cloudflared:  winget install --id Cloudflare.cloudflared
"""

import os
import re
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
PUERTO = os.environ.get("DEMO_PUERTO", "8000")
ARCHIVO_CLAVE = BASE / ".demo_secret_key"  # en .gitignore
CLAVES_DE_EJEMPLO = {"admin1234", "demo1234"}


def clave_secreta():
    if not ARCHIVO_CLAVE.exists():
        ARCHIVO_CLAVE.write_text(secrets.token_urlsafe(50), encoding="utf-8")
    return ARCHIVO_CLAVE.read_text(encoding="utf-8").strip()


def configurar_entorno():
    os.environ.update({
        "DJANGO_DEBUG": "0",
        "DJANGO_SECRET_KEY": clave_secreta(),
        "DJANGO_ALLOWED_HOSTS": "127.0.0.1,localhost,.trycloudflare.com",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "https://*.trycloudflare.com",
        "DJANGO_HTTPS": "1",
        "DJANGO_HTTPS_REDIRIGIR": "0",  # el túnel ya es https
        "DJANGO_IP_CABECERA": "Cf-Connecting-IP",  # IP real del visitante (límite de intentos)
        "DJANGO_SERVIR_MEDIA": "1",
    })


def manage(*args):
    subprocess.run([sys.executable, str(BASE / "manage.py"), *args], cwd=BASE, check=True)


def cuentas_con_clave_de_ejemplo():
    """Usuarios del equipo interno que siguen con una contraseña publicada en el README."""
    sys.path.insert(0, str(BASE))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()
    from django.contrib.auth import get_user_model

    from apps.core.mixins import es_personal

    return [
        u.username for u in get_user_model().objects.filter(is_active=True)
        if es_personal(u) and any(u.check_password(c) for c in CLAVES_DE_EJEMPLO)
    ]


def main():
    cloudflared = shutil.which("cloudflared")
    if not cloudflared:
        sys.exit(
            "No se encontró cloudflared. Instálalo con:\n"
            "    winget install --id Cloudflare.cloudflared\n"
            "y vuelve a abrir esta ventana."
        )
    configurar_entorno()
    print("» Preparando archivos y base de datos...")
    manage("collectstatic", "--noinput", "-v", "0")
    manage("migrate", "--noinput", "-v", "0")

    inseguras = cuentas_con_clave_de_ejemplo()
    if inseguras:
        sys.exit(
            "\nNo se publica: estas cuentas del equipo usan una contraseña de ejemplo "
            "(publicada en el README):\n    " + ", ".join(inseguras) +
            "\nCámbialas con, por ejemplo:\n    " +
            "\n    ".join(f"python manage.py changepassword {u}" for u in inseguras)
        )

    print(f"» Iniciando SpaceWise en http://127.0.0.1:{PUERTO} ...")
    # Solo escucha en este PC; desde internet se llega únicamente por el túnel.
    servidor = subprocess.Popen(
        [sys.executable, str(BASE / "manage.py"), "runserver", f"127.0.0.1:{PUERTO}", "--noreload"], cwd=BASE
    )
    tunel = subprocess.Popen(
        [cloudflared, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{PUERTO}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
    )
    print("» Abriendo el túnel de Cloudflare (puede tardar unos segundos)...")
    try:
        for linea in tunel.stdout:
            url = re.search(r"https://[-a-z0-9]+\.trycloudflare\.com", linea)
            if url:
                print("\n" + "=" * 64)
                print(f"  SpaceWise está publicado en:  {url.group(0)}")
                print("  Comparte esa dirección. Para apagar todo: Ctrl+C")
                print("=" * 64 + "\n")
            elif "ERR" in linea:
                print("[túnel]", linea.rstrip())
        tunel.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for proceso in (tunel, servidor):
            if proceso.poll() is None:
                proceso.terminate()
        print("\nDemo detenida.")


if __name__ == "__main__":
    main()
