#!/usr/bin/env bash
set -e

echo "Waiting for database..."
python manage.py wait_for_db 2>/dev/null || true

echo "Running migrations..."
python manage.py migrate --noinput

echo "Starting server..."
exec "$@"
