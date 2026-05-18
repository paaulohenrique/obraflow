#!/usr/bin/env bash
# Usage: docker compose exec backend bash scripts/create_superuser.sh
set -e

python manage.py shell -c "
from apps.empresas.models import Empresa
from apps.accounts.models import User

# Create the default empresa if it doesn't exist
empresa, created = Empresa.objects.get_or_create(
    cnpj='00000000000191',
    defaults={
        'razao_social': 'ObraFlow Demo',
        'nome_fantasia': 'ObraFlow',
        'plano': Empresa.PLANO_PROFISSIONAL,
        'limite_usuarios': 100,
    },
)
if created:
    print(f'Empresa criada: {empresa.razao_social} ({empresa.id})')
else:
    print(f'Empresa existente: {empresa.razao_social} ({empresa.id})')

# Create the superuser if it doesn't exist
if not User.objects.filter(email='admin@obraflow.com').exists():
    User.objects.create_superuser(
        email='admin@obraflow.com',
        name='Admin',
        password='admin123',
        company=empresa,
    )
    print('Superuser created: admin@obraflow.com / admin123')
else:
    # Ensure existing admin has a company
    admin = User.objects.get(email='admin@obraflow.com')
    if admin.company is None:
        admin.company = empresa
        admin.save(update_fields=['company'])
        print(f'Admin company set to: {empresa.razao_social}')
    else:
        print('Superuser already exists.')
"
