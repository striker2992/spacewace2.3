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

# Aplicar migraciones de la base de datos
echo "Aplicando migraciones..."
python manage.py migrate --noinput

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
