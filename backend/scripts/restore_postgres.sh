#!/usr/bin/env bash
# restore_postgres.sh — Restore do banco ObraFlow a partir de backup
#
# Uso:
#   ./scripts/restore_postgres.sh /app/backups/obraflow_20260603_120000.sql.gz
#
# ATENÇÃO: Este script DROP e recria o banco. Use apenas em ambientes controlados.
#
# Variáveis de ambiente:
#   DB_HOST      — padrão: db
#   DB_PORT      — padrão: 5432
#   DB_NAME      — padrão: obraflow
#   DB_USER      — padrão: obraflow
#   DB_PASSWORD  — padrão: obraflow
set -euo pipefail

BACKUP_FILE="${1:-}"
if [ -z "${BACKUP_FILE}" ]; then
    echo "ERRO: Informe o arquivo de backup."
    echo "Uso: $0 /caminho/para/obraflow_YYYYMMDD_HHMMSS.sql.gz"
    exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "ERRO: Arquivo não encontrado: ${BACKUP_FILE}"
    exit 1
fi

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-obraflow}"
DB_USER="${DB_USER:-obraflow}"
DB_PASSWORD="${DB_PASSWORD:-obraflow}"

echo "============================================================"
echo " RESTORE DE BANCO DE DADOS"
echo "============================================================"
echo " Arquivo   : ${BACKUP_FILE}"
echo " Banco     : ${DB_NAME} @ ${DB_HOST}:${DB_PORT}"
echo " Tamanho   : $(du -sh "${BACKUP_FILE}" | cut -f1)"
echo "============================================================"
echo ""
echo "ATENÇÃO: O banco atual (${DB_NAME}) será APAGADO e recriado."
read -rp "Digite 'CONFIRMAR' para continuar: " CONFIRM

if [ "${CONFIRM}" != "CONFIRMAR" ]; then
    echo "Operação cancelada."
    exit 0
fi

export PGPASSWORD="${DB_PASSWORD}"

echo "[restore] Encerrando conexões ativas..."
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid <> pg_backend_pid();" \
    > /dev/null 2>&1 || true

echo "[restore] Recriando banco..."
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c \
    "DROP DATABASE IF EXISTS ${DB_NAME};" > /dev/null
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c \
    "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};" > /dev/null

echo "[restore] Restaurando dados..."
gunzip -c "${BACKUP_FILE}" | psql \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    -q

echo "[restore] Validando restore..."
TABELAS="$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")"
echo "[restore] Tabelas encontradas: ${TABELAS// /}"

echo ""
echo "============================================================"
echo " RESTORE CONCLUÍDO COM SUCESSO"
echo " $(date)"
echo "============================================================"
