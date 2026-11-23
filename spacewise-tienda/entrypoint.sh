#!/usr/bin/env bash
set -e

# Esperar a que la base de datos MySQL esté disponible
if [ -n "$DB_HOST" ]; then
    echo "Esperando a que la base de datos MySQL en $DB_HOST:$DB_PORT esté disponible..."
    while ! nc -z "$DB_HOST" "${DB_PORT:-3306}"; do
        sleep 1
    done
    echo "MySQL está listo para aceptar conexiones."
fi

# Sincronización y autocorrección de credenciales de usuario en MySQL
# Si se cambia DB_PASSWORD o DB_USER en el .env con un volumen persistente ya existente,
# este script reconecta como root y asegura que el usuario, base de datos y contraseña
# coincidan exactamente con la configuración actual, evitando el error 1045 Access Denied.
python - << 'EOF'
import os
import sys
import time

try:
    import MySQLdb
except ImportError:
    sys.exit(0)

host = os.environ.get("DB_HOST", "db")
port = int(os.environ.get("DB_PORT", "3306"))
user = os.environ.get("DB_USER", "spacewise")
password = os.environ.get("DB_PASSWORD", "spacewise_secret_pass")
root_password = os.environ.get("DB_ROOT_PASSWORD", "root_secret_pass")
db_name = os.environ.get("DB_NAME", "spacewise_db")

# 1. Probar si las credenciales de la app ya funcionan
conectado = False
for _ in range(5):
    try:
        conn = MySQLdb.connect(host=host, port=port, user=user, passwd=password, db=db_name)
        conn.close()
        conectado = True
        print(f"Credenciales de '{user}' verificadas correctamente.")
        break
    except Exception:
        time.sleep(1)

# 2. Si falló la autenticación, corregir y sincronizar usando la cuenta root
if not conectado:
    print(f"Sincronizando usuario '{user}' y permisos en MySQL con la configuración actual...")
    try:
        conn = MySQLdb.connect(host=host, port=port, user="root", passwd=root_password)
        cursor = conn.cursor()
        
        # Crear base si no existe
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        
        # Crear o actualizar usuario con la contraseña actual
        cursor.execute(f"CREATE USER IF NOT EXISTS '{user}'@'%' IDENTIFIED BY %s;", (password,))
        cursor.execute(f"ALTER USER '{user}'@'%' IDENTIFIED BY %s;", (password,))
        cursor.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{user}'@'%';")
        cursor.execute("FLUSH PRIVILEGES;")
        
        cursor.close()
        conn.close()
        print(f"Usuario '{user}' y contraseña sincronizados exitosamente con MySQL.")
    except Exception as e:
        print(f"Aviso al sincronizar credenciales: {e}")
EOF

# Sincronizar y aplicar migraciones de la base de datos
echo "Sincronizando estado de migraciones..."
python manage.py migrate --fake-initial --noinput || true
python manage.py migrate --noinput || true

# Recolectar archivos estáticos para WhiteNoise
echo "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

# Opcional: cargar datos iniciales si la variable SEED_DATABASE está en 1
if [ "$SEED_DATABASE" = "1" ]; then
    echo "Ejecutando seed de datos iniciales..."
    python manage.py seed || true
fi

echo "Iniciando proceso principal: $@"
exec "$@"
