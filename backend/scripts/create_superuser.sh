#!/usr/bin/env bash
# Usage: docker compose exec backend bash scripts/create_superuser.sh
set -e

python manage.py shell -c "
from apps.accounts.models import User
if not User.objects.filter(email='admin@obraflow.com').exists():
    User.objects.create_superuser(
        email='admin@obraflow.com',
        name='Admin',
        password='admin123',
    )
    print('Superuser created: admin@obraflow.com / admin123')
else:
    print('Superuser already exists.')
"
