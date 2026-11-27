#!/usr/bin/env bash
# ==============================================================================
# SpaceWise Tienda - Script de Respaldo Diario Automatizado de Base de Datos MySQL
# ==============================================================================
# - Realiza un dump comprimido (.sql.gz) de la base de datos MySQL en Docker
# - Guarda los respaldos en /opt/spacewace2.3/backups
# - Elimina automáticamente respaldos con más de 7 días de antigüedad
# - Configurar en crontab: 0 3 * * * /opt/spacewace2.3/spacewise-tienda/deploy/backup_diario.sh >> /var/log/spacewise_backup.log 2>&1
# ==============================================================================

set -euo pipefail

PROYECTO_DIR="/opt/spacewace2.3/spacewise-tienda"
BACKUP_DIR="/opt/spacewace2.3/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/backup_spacewise_${TIMESTAMP}.sql.gz"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando respaldo de base de datos SpaceWise..."

# Crear carpeta de respaldos si no existe
mkdir -p "${BACKUP_DIR}"

# Cargar variables de entorno si existen
if [ -f "${PROYECTO_DIR}/.env" ]; then
    # Extraer variables ignorando comentarios y líneas vacías
    DB_USER=$(grep -E '^DB_USER=' "${PROYECTO_DIR}/.env" | cut -d '=' -f2- | tr -d '\r"' || echo "spacewise")
    DB_PASSWORD=$(grep -E '^DB_PASSWORD=' "${PROYECTO_DIR}/.env" | cut -d '=' -f2- | tr -d '\r"' || echo "spacewise_secret_pass")
    DB_NAME=$(grep -E '^DB_NAME=' "${PROYECTO_DIR}/.env" | cut -d '=' -f2- | tr -d '\r"' || echo "spacewise_db")
else
    DB_USER="spacewise"
    DB_PASSWORD="spacewise_secret_pass"
    DB_NAME="spacewise_db"
fi

# Ejecutar mysqldump a través de docker compose y comprimir en gzip
cd "${PROYECTO_DIR}"

if docker compose exec -T db mysqldump -u "${DB_USER}" -p"${DB_PASSWORD}" \
    --default-character-set=utf8mb4 \
    --single-transaction \
    --quick \
    "${DB_NAME}" | gzip > "${BACKUP_FILE}"; then
    
    TAMANO=$(ls -lh "${BACKUP_FILE}" | awk '{print $5}')
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Respaldo completado exitosamente: ${BACKUP_FILE} (Tamaño: ${TAMANO})"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Falló la creación del respaldo." >&2
    exit 1
fi

# Eliminar respaldos con más de 7 días de antigüedad
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Rotando respaldos antiguos (más de 7 días)..."
ELIMINADOS=$(find "${BACKUP_DIR}" -type f -name "backup_spacewise_*.sql.gz" -mtime +7 -print -delete | wc -l)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Se eliminaron ${ELIMINADOS} respaldo(s) antiguo(s)."

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Proceso de backup finalizado con éxito."
