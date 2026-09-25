#!/usr/bin/env bash
set -euo pipefail

# Cargar .env
if [ -f .env ]; then
    set -a; . ./.env; set +a
fi

: "${MYSQL_USER:?MYSQL_USER no definido}"
: "${MYSQL_PASSWORD:?MYSQL_PASSWORD no definido}"
: "${MYSQL_DB:?MYSQL_DB no definido}"

BACKUP_DIR="${BACKUP_DIR:-backups}"
mkdir -p "$BACKUP_DIR"

FECHA=$(date +%F_%H-%M)
ARCHIVO="$BACKUP_DIR/${MYSQL_DB}_${FECHA}.sql.gz"

echo "[$(date)] Backup -> $ARCHIVO"

mysqldump \
    -h "${MYSQL_HOST:-localhost}" \
    -P "${MYSQL_PORT:-3306}" \
    -u "$MYSQL_USER" \
    -p"$MYSQL_PASSWORD" \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --databases "$MYSQL_DB" | gzip > "$ARCHIVO"

# Rotar: borrar > 30 dias
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete

echo "[$(date)] OK"