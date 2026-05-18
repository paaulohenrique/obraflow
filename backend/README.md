# ObraFlow — Backend

ERP para lojas de material de construção. Stack: **Python 3.12 · Django 5.2 · DRF · PostgreSQL · Redis · Celery**.

---

## Subir com Docker (recomendado)

```bash
# 1. Clone e entre na raiz do repositório
cd obraflow

# 2. Copie o .env (já feito se você usou o setup automático)
cp backend/.env.example backend/.env
# Edite backend/.env com suas variáveis

# 3. Suba todos os serviços
docker compose up --build

# 4. Em outro terminal, rode as migrations e crie o superusuário
docker compose exec backend python manage.py migrate
docker compose exec backend bash scripts/create_superuser.sh
```

Acesse:
- API: http://localhost:8000/api/v1/
- Health: http://localhost:8000/api/health/
- Docs (Swagger): http://localhost:8000/api/v1/docs/
- Admin: http://localhost:8000/admin/

---

## Setup local (sem Docker)

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt

cp .env.example .env
# Edite .env apontando para Postgres/Redis locais

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Celery (separado):
```bash
celery -A config.celery worker --loglevel=info
celery -A config.celery beat --loglevel=info
```

---

## Testes

```bash
pytest                    # todos os testes
pytest -m "not slow"      # exclui testes lentos
pytest apps/core/         # testa só o core
pytest --cov=apps         # com cobertura
```

---

## Variáveis de ambiente

| Variável | Descrição | Default |
|---|---|---|
| `SECRET_KEY` | Chave secreta Django | — |
| `DEBUG` | Modo debug | `False` |
| `DATABASE_URL` | DSN do PostgreSQL | — |
| `REDIS_URL` | URL do Redis (cache) | — |
| `CELERY_BROKER_URL` | URL do broker Celery | — |
| `CELERY_RESULT_BACKEND` | Backend de resultados | `django-db` |
| `JWT_ACCESS_MINUTES` | Validade do access token | `60` |
| `JWT_REFRESH_DAYS` | Validade do refresh token | `7` |
| `CORS_ALLOWED_ORIGINS` | Origens permitidas no CORS | — |

---

## Estrutura de apps

| App | Responsabilidade |
|---|---|
| `core` | BaseModel, AuditLog, paginação, exceções, middleware |
| `accounts` | Autenticação JWT, usuários, roles |
| `clientes` | Cadastro de clientes |
| `fiado` | Controle de crédito informal |
| `financeiro` | Contas a pagar/receber, fluxo de caixa |
| `estoque` | Produtos, movimentações |
| `fiscal` | NF-e, NFC-e |
| `cobrancas` | Cobranças automáticas |
| `boletos` | OCR e emissão de boletos |
| `notificacoes` | WhatsApp, e-mail, push |
| `relatorios` | PDFs, dashboards |

---

## Padrão arquitetural por app

```
apps/nome_app/
├── models.py       → entidades do banco
├── serializers.py  → validação e serialização
├── views.py        → ViewSets / APIViews
├── urls.py         → roteamento
├── services.py     → lógica de negócio (mutations)
├── selectors.py    → queries de leitura
├── tasks.py        → tarefas Celery
├── permissions.py  → permissões customizadas
├── admin.py        → admin Django
├── migrations/
└── tests/
```
