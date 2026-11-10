#!/usr/bin/env bash
# Instala o actualiza SpaceWise en un servidor Ubuntu 24.04 / Debian (p. ej. una VM del iLab).
#
#   Primera vez:   curl -fsSL https://raw.githubusercontent.com/striker2992/spacewace2.3/main/spacewise-tienda/deploy/instalar_servidor.sh -o instalar.sh
#                  sudo bash instalar.sh
#   Actualizar:    sudo bash /opt/spacewise/repo/spacewise-tienda/deploy/instalar_servidor.sh
#
# Deja: MySQL con su base y usuario, el código en /opt/spacewise, gunicorn como servicio
# «spacewise» y Nginx en el puerto 80. Volver a ejecutarlo actualiza sin perder datos.
# Opcional: SPACEWISE_HOSTS="nombre.dominio,otra-ip" agrega direcciones permitidas.
set -euo pipefail

REPO_URL="${SPACEWISE_REPO:-https://github.com/striker2992/spacewace2.3}"
RAMA="${SPACEWISE_RAMA:-main}"
BASE=/opt/spacewise
REPO="$BASE/repo"
APP="$REPO/spacewise-tienda"
VENV="$BASE/venv"
USUARIO=spacewise
PUERTO_APP=8000

paso() { printf '\n\033[1;34m» %s\033[0m\n' "$*"; }
falla() { printf '\n\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }
aleatorio() { python3 -c "import secrets; print(secrets.token_urlsafe($1))"; }
hay_systemd() { [ -d /run/systemd/system ]; }

[ "$(id -u)" -eq 0 ] || falla "Ejecútalo con sudo:  sudo bash $0"
command -v apt-get >/dev/null || falla "Este script es para Ubuntu o Debian."

paso "Paquetes del sistema"
export DEBIAN_FRONTEND=noninteractive
if ! apt-get update -qq; then
  # Las VM del iLab usan un proxy caché de apt que falla con repositorios HTTPS (ver su guía).
  if [ -f /etc/apt/apt.conf.d/90curtin-aptproxy ]; then
    echo "apt falló: se quita el proxy caché del iLab y se reintenta."
    rm -f /etc/apt/apt.conf.d/90curtin-aptproxy
    apt-get update -qq
  else
    falla "apt-get update falló. Revisa la conexión a internet de la máquina."
  fi
fi
SERVIDOR_BD=mysql-server
apt-cache show mysql-server >/dev/null 2>&1 || SERVIDOR_BD=default-mysql-server  # Debian: MariaDB
apt-get install -y -qq git curl python3 python3-venv python3-dev build-essential pkg-config \
  default-libmysqlclient-dev "$SERVIDOR_BD" nginx >/dev/null

paso "Base de datos"
if hay_systemd; then systemctl enable --now mysql >/dev/null 2>&1 || systemctl enable --now mariadb >/dev/null; else service mysql start >/dev/null 2>&1 || service mariadb start >/dev/null; fi
for _ in $(seq 30); do mysqladmin ping --silent >/dev/null 2>&1 && break; sleep 1; done
mysqladmin ping --silent >/dev/null 2>&1 || falla "MySQL no arrancó."

paso "Código de SpaceWise"
id "$USUARIO" >/dev/null 2>&1 || useradd --system --home "$BASE" --shell /usr/sbin/nologin "$USUARIO"
mkdir -p "$BASE"
git config --global --add safe.directory "$REPO" >/dev/null 2>&1 || true
if [ -d "$REPO/.git" ]; then
  git -C "$REPO" fetch -q origin "$RAMA" && git -C "$REPO" checkout -q "$RAMA" && git -C "$REPO" reset -q --hard "origin/$RAMA"
else
  git clone -q --branch "$RAMA" "$REPO_URL" "$REPO"
fi
echo "Versión: $(git -C "$REPO" log --oneline -1)"

paso "Entorno de Python y dependencias"
[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$APP/requirements.txt"

paso "Configuración (.env)"
ENV="$APP/.env"
if [ ! -f "$ENV" ]; then
  # El .env vive en $APP; se respalda fuera del repositorio para que «git reset» nunca lo toque.
  [ -f "$BASE/.env" ] && cp "$BASE/.env" "$ENV"
fi
if [ ! -f "$ENV" ]; then
  IP=$(hostname -I 2>/dev/null | awk '{print $1}')
  HOSTS="127.0.0.1,localhost,$(hostname),$(hostname -f 2>/dev/null || hostname)${IP:+,$IP}${SPACEWISE_HOSTS:+,$SPACEWISE_HOSTS}"
  cat > "$ENV" <<EOF
# Generado por instalar_servidor.sh — no lo subas a GitHub.
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=$(aleatorio 50)
DJANGO_ALLOWED_HOSTS=$HOSTS
# Red interna de la universidad, sin HTTPS. Si algún día hay dominio con certificado: DJANGO_HTTPS=1
DJANGO_HTTPS=0
# Nginx sirve /media/ y pasa la IP real del visitante en X-Real-IP
DJANGO_SERVIR_MEDIA=0
DJANGO_IP_CABECERA=X-Real-IP
DB_NAME=spacewise_db
DB_USER=spacewise
DB_PASSWORD=$(aleatorio 24)
DB_HOST=127.0.0.1
DB_PORT=3306
EOF
  echo "Creado $ENV"
else
  echo "Se conserva el .env existente."
fi
chmod 600 "$ENV"
cp "$ENV" "$BASE/.env" && chmod 600 "$BASE/.env"
DB_PASSWORD=$(grep '^DB_PASSWORD=' "$ENV" | cut -d= -f2-)

mysql <<EOF
CREATE DATABASE IF NOT EXISTS spacewise_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'spacewise'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
ALTER USER 'spacewise'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON spacewise_db.* TO 'spacewise'@'localhost';
FLUSH PRIVILEGES;
EOF

paso "Migraciones, archivos estáticos y datos de demostración"
mkdir -p "$APP/media"
chown -R "$USUARIO:$USUARIO" "$BASE"
como() { (cd "$APP" && runuser -u "$USUARIO" -- "$VENV/bin/python" manage.py "$@"); }
como migrate --noinput -v 0
como collectstatic --noinput -v 0
CLAVE_NUEVA=""
if ! como shell -c "from django.contrib.auth.models import User; import sys; sys.exit(0 if User.objects.filter(username='admin').exists() else 1)" >/dev/null 2>&1; then
  CLAVE_NUEVA=$(aleatorio 12)
  como seed --clave-equipo "$CLAVE_NUEVA"
  # Se guarda por si la instalación se interrumpe antes de mostrarla (solo root puede leerla).
  ( umask 077; echo "admin, ana, luis y marta: $CLAVE_NUEVA" > /root/spacewise_clave_equipo.txt )
fi
chmod 755 "$BASE" "$REPO" "$APP"

paso "Servicio de la aplicación (gunicorn)"
cat > /etc/systemd/system/spacewise.service <<EOF
[Unit]
Description=SpaceWise (gunicorn)
After=network.target mysql.service mariadb.service

[Service]
User=$USUARIO
Group=$USUARIO
WorkingDirectory=$APP
ExecStart=$VENV/bin/gunicorn config.wsgi --bind 127.0.0.1:$PUERTO_APP --workers 1 --threads 4 --access-logfile -
Restart=always

[Install]
WantedBy=multi-user.target
EOF
if hay_systemd; then
  systemctl daemon-reload
  systemctl enable spacewise >/dev/null 2>&1
  systemctl restart spacewise
else
  # Sin systemd (contenedores, WSL): se inicia en segundo plano y no arranca solo al reiniciar.
  pkill -f "gunicorn config.wsgi" 2>/dev/null || true
  (cd "$APP" && runuser -u "$USUARIO" -- nohup "$VENV/bin/gunicorn" config.wsgi --bind 127.0.0.1:$PUERTO_APP \
    --workers 1 --threads 4 >"$BASE/gunicorn.log" 2>&1 &)
fi

paso "Servidor web (Nginx)"
cat > /etc/nginx/sites-available/spacewise <<EOF
server {
    listen 80 default_server;
    server_name _;
    client_max_body_size 10M;

    location /static/ { alias $APP/staticfiles/; expires 30d; }
    location /media/  { alias $APP/media/; }

    location / {
        proxy_pass http://127.0.0.1:$PUERTO_APP;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
ln -sf /etc/nginx/sites-available/spacewise /etc/nginx/sites-enabled/spacewise
rm -f /etc/nginx/sites-enabled/default
nginx -t -q
if hay_systemd; then systemctl enable nginx >/dev/null 2>&1; systemctl reload-or-restart nginx; else service nginx restart >/dev/null 2>&1 || nginx; fi

paso "Comprobación"
CODIGO=000
for _ in $(seq 20); do
  CODIGO=$(curl -s -o /dev/null -w '%{http_code}' -H "Host: 127.0.0.1" http://127.0.0.1/catalogo/ || true)
  [ "$CODIGO" = 200 ] && break; sleep 1
done
[ "$CODIGO" = 200 ] || falla "SpaceWise no respondió (código $CODIGO). Revisa: journalctl -u spacewise -n 50"

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
printf '\n\033[1;32m✓ SpaceWise está funcionando\033[0m\n'
echo "  Dirección:  http://${IP:-IP-del-servidor}/   (desde la red de la universidad / eduroam)"
if [ -n "$CLAVE_NUEVA" ]; then
  echo "  Equipo:     admin, ana, luis y marta  /  contraseña: $CLAVE_NUEVA   (anótala y cámbiala;"
  echo "              también quedó en /root/spacewise_clave_equipo.txt)"
  echo "  Tienda:     camila@ejemplo.cl / demo1234"
fi
echo "  Actualizar: sudo bash $APP/deploy/instalar_servidor.sh"
echo "  Registros:  journalctl -u spacewise -f"
