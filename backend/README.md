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
├── models.py         → entidades do banco
├── serializers.py    → validação e serialização
├── views.py          → ViewSets / APIViews (sem lógica de negócio)
├── urls.py           → roteamento
├── services/         → lógica de negócio (mutations) — pacote ou arquivo
│   ├── __init__.py   →   re-exporta símbolos públicos
│   └── <dominio>.py  →   funções de mutação por subdomínio
├── selectors.py      → queries de leitura (retornam QuerySet ou objeto)
├── filters.py        → FilterSets (django-filter) — schema Swagger
├── validators.py     → validações de domínio puras
├── tasks.py          → tarefas Celery
├── permissions.py    → permissões customizadas por app
├── admin.py          → admin Django
├── migrations/
└── tests/
    ├── conftest.py   → fixtures e factories do app
    ├── test_models.py
    ├── test_services.py
    ├── test_selectors.py
    ├── test_views.py
    └── test_validators.py
```

### Regras de services

**Padrão oficial:** `apps/<app>/services/` como pacote Python.

```python
# apps/<app>/services/__init__.py — re-exporta o que views.py precisa
from .cliente import create_cliente, update_cliente, soft_delete_cliente

# apps/<app>/services/<dominio>.py — funções puras com @transaction.atomic
@transaction.atomic
def create_cliente(*, user, data: dict, request=None) -> Cliente:
    require_company(user)   # guard multi-tenant obrigatório
    ...
    create_audit_log(...)
    return cliente
```

**Regras:**
- Toda função de mutação usa `@transaction.atomic`
- `require_company(user)` é chamado no topo de toda função tenant-scoped
- Views não contêm Q objects — busca e filtros ficam em `selectors.py`
- `selectors.py` não importa de `services/` e vice-versa
- `AuditLog` é criado no service, nunca na view ou no model

---

## Segurança (Sprint 0)

| Proteção | Implementação |
|---|---|
| Brute force login | `LoginRateThrottle` — 5 req/min por IP |
| User sem empresa | `require_company()` em permissions + services |
| Tenant isolation | `_base_qs(company_id)` levanta `PermissionDenied` se `None` |
| AuditLog imutável | `soft_delete()` e `delete()` levantam `RuntimeError` |
| Request tracing | `X-Request-ID` injetado pelo middleware em toda resposta |
| Headers de produção | HSTS, XSS, nosniff, X-Frame-Options |
| Stacktrace em prod | Desabilitado — Sentry recebe, cliente não vê |

---

## Observabilidade

- **Request ID**: Cada request recebe `X-Request-ID` (UUID gerado ou propagado do header de entrada). Aparece nos logs e no envelope de erro.
- **AuditLog**: Toda mutação registra `user`, `action`, `entity_type`, `entity_id`, `before`, `after`, `ip`, `user_agent`.
- **HealthCheck**: `GET /api/health/` verifica DB e Redis, retorna `503` se indisponível.
- **Logs**: `RequestLoggingMiddleware` loga `METHOD PATH STATUS DURATIONms request_id=...`.
