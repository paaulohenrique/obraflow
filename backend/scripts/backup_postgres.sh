#!/usr/bin/env bash
# backup_postgres.sh — Backup do banco ObraFlow
#
# Uso local:
#   ./scripts/backup_postgres.sh
#
# Com upload S3:
#   S3_BUCKET=s3://meu-bucket/backups ./scripts/backup_postgres.sh
#
# Variáveis de ambiente (padrões do docker-compose.yml):
#   DB_HOST      — padrão: db
#   DB_PORT      — padrão: 5432
#   DB_NAME      — padrão: obraflow
#   DB_USER      — padrão: obraflow
#   DB_PASSWORD  — padrão: obraflow
#   BACKUP_DIR   — padrão: /app/backups
#   S3_BUCKET    — opcional; se definido, faz upload via aws s3 cp
#   KEEP_DAYS    — padrão: 7 (remove backups locais mais antigos)
set -euo pipefail

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-obraflow}"
DB_USER="${DB_USER:-obraflow}"
DB_PASSWORD="${DB_PASSWORD:-obraflow}"
BACKUP_DIR="${BACKUP_DIR:-/app/backups}"
S3_BUCKET="${S3_BUCKET:-}"
KEEP_DAYS="${KEEP_DAYS:-7}"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
FILENAME="obraflow_${TIMESTAMP}.sql.gz"
FILEPATH="${BACKUP_DIR}/${FILENAME}"

mkdir -p "${BACKUP_DIR}"

echo "[backup] Iniciando dump: ${FILENAME}"
PGPASSWORD="${DB_PASSWORD}" pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --no-password \
    --format=plain \
    --no-owner \
    --no-acl \
    | gzip -9 > "${FILEPATH}"

SIZE="$(du -sh "${FILEPATH}" | cut -f1)"
echo "[backup] Dump concluído: ${FILEPATH} (${SIZE})"

# Upload para S3/GCS (requer aws cli ou gsutil configurados)
if [ -n "${S3_BUCKET}" ]; then
    echo "[backup] Enviando para ${S3_BUCKET}/${FILENAME}..."
    if command -v aws &>/dev/null; then
        aws s3 cp "${FILEPATH}" "${S3_BUCKET}/${FILENAME}"
        echo "[backup] Upload S3 concluído."
    elif command -v gsutil &>/dev/null; then
        gsutil cp "${FILEPATH}" "${S3_BUCKET}/${FILENAME}"
        echo "[backup] Upload GCS concluído."
    else
        echo "[backup] AVISO: S3_BUCKET definido mas nenhum cliente (aws/gsutil) encontrado."
    fi
fi

# Remove backups locais mais antigos que KEEP_DAYS dias
echo "[backup] Removendo backups com mais de ${KEEP_DAYS} dias..."
find "${BACKUP_DIR}" -name "obraflow_*.sql.gz" -mtime "+${KEEP_DAYS}" -delete
RESTANTES="$(find "${BACKUP_DIR}" -name "obraflow_*.sql.gz" | wc -l | tr -d ' ')"
echo "[backup] Backups locais mantidos: ${RESTANTES}"

echo "[backup] Concluído em $(date)"
