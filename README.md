# 🏗️ ObraFlow

> ERP completo para lojas de material de construção — controle de fiado, financeiro, estoque, cobranças automáticas e emissão fiscal em um único lugar.

---

## 📋 Sobre o projeto

O **ObraFlow** foi desenvolvido para resolver os problemas reais do dia a dia de uma loja de material de construção. Clientes compram materiais fiado ao longo de vários dias, pagamentos são parciais, boletos precisam ser controlados, notas precisam ser emitidas e cobranças precisam ser enviadas — tudo isso reunido em uma plataforma centralizada.

### Problemas que resolve

- Controle de fiado com acúmulo de compras por cliente ao longo dos dias
- Pagamentos parciais com saldo atualizado automaticamente
- Cobranças automáticas via WhatsApp e e-mail
- OCR de boletos: tira foto → sistema lê e cadastra automaticamente
- Emissão de NF-e e NFS-e integrada
- Dashboard financeiro com visão diária, mensal e anual
- Controle de estoque com alertas de quantidade baixa

---

## 🚀 Stack tecnológica

### Frontend
| Tecnologia | Versão | Uso |
|---|---|---|
| Next.js | 16 | Framework React com SSR |
| React | 19 | Interface de usuário |
| TypeScript | — | Tipagem estática |
| Tailwind CSS | v4 | Estilização |
| Shadcn/UI | — | Componentes de interface |
| React Hook Form | — | Gerenciamento de formulários |
| Zod | — | Validação de dados |
| TanStack Query | — | Cache e sincronização de dados |
| Recharts | — | Gráficos do dashboard |

### Backend
| Tecnologia | Versão | Uso |
|---|---|---|
| Python | 3.12+ | Linguagem principal |
| Django | 5.2 | Framework web |
| Django REST Framework | — | API REST |
| SimpleJWT | — | Autenticação JWT |
| Celery | — | Filas e tarefas assíncronas |
| Redis | — | Broker do Celery e cache |
| WeasyPrint | — | Geração de PDF |

### Banco de dados
| Tecnologia | Uso |
|---|---|
| PostgreSQL | Banco principal (dev e produção) |

### Integrações externas
| Serviço | Finalidade |
|---|---|
| Google Vision API | OCR de boletos |
| Z-API | Envio de mensagens via WhatsApp |
| Resend | Envio de e-mails transacionais |
| NFE.io / PlugNotas | Emissão de NF-e e NFS-e |
| Cloudflare R2 | Armazenamento de arquivos (PDF, XML, imagens) |
| ViaCEP | Preenchimento automático de endereço |

### Infraestrutura
| Tecnologia | Uso |
|---|---|
| Docker + Docker Compose | Containerização e ambiente local |
| Vercel | Deploy do frontend |
| Railway | Deploy do backend + Redis + Celery |
| Supabase | PostgreSQL gerenciado em produção |

---

## ✨ Funcionalidades

### Dashboard
- Recebido hoje / no mês / no ano
- Contas a pagar e valores a receber
- Clientes em atraso
- Produtos com estoque baixo
- Gráficos e alertas automáticos

### Cadastro de clientes
- Dados completos com CPF/CNPJ
- Preenchimento automático de endereço via CEP
- Limite de crédito configurável

### Sistema de fiado
- Notas abertas com acúmulo de compras por dias
- Pagamentos parciais com saldo atualizado em tempo real
- Status: Em aberto / Parcial / Fechada
- Fechamento automático ao quitar o saldo
- Impressão e exportação em PDF

### Financeiro
- Controle de entradas e saídas
- Balanço diário, mensal e anual
- Abertura e fechamento de caixa diário
- Lançamentos manuais com histórico

### Contas a pagar
- Cadastro manual ou via foto do boleto
- OCR automático: valor, vencimento, banco e código de barras
- Histórico completo de pagamentos

### Estoque
- Cadastro de produtos com categorias e fornecedores
- Alertas de estoque baixo
- Cálculo automático de margem de lucro
- Histórico de movimentações

### Emissão fiscal
- NF-e e NFS-e
- Prévia antes de emitir
- Download de PDF (DANFE) e XML
- Cancelamento e histórico
- Envio automático por WhatsApp e e-mail após emissão

### Cobranças automáticas
- Envio de cobranças por WhatsApp e e-mail
- Agendamento via Celery
- Histórico de envios com data, hora e status

---

## 🗂️ Estrutura do projeto

```
obraflow/
├── backend/
│   ├── apps/
│   │   ├── clientes/
│   │   ├── fiado/
│   │   ├── financeiro/
│   │   ├── estoque/
│   │   └── notificacoes/
│   ├── config/
│   ├── Dockerfile
│   └── manage.py
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   ├── services/
│   │   └── types/
│   └── package.json
├── docker-compose.yml
├── docker-compose.test.yml
├── package.json
└── README.md
```

---

## ⚙️ Como rodar localmente

### Pré-requisitos

- [Docker](https://www.docker.com/) e Docker Compose instalados
- [Node.js](https://nodejs.org/) 20+
- [Python](https://www.python.org/) 3.12+

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/obraflow.git
cd obraflow
```

### 2. Configure as variáveis de ambiente

```bash
cp backend/.env.example backend/.env
```

Edite os arquivos `.env` com suas credenciais.

### 3. Suba os containers

```bash
docker compose up -d
```

Isso vai iniciar:
- Django (porta 8000)
- PostgreSQL (porta 5433 no host)
- Redis (porta 6380 no host)

### 4. Execute as migrations

```bash
docker compose exec backend python manage.py migrate
```

### 5. Crie um superusuário

```bash
docker compose exec backend python manage.py createsuperuser
```

### 6. Acesse o sistema

| Serviço | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000/api/ |
| Django Admin | http://localhost:8000/admin/ |
| API Docs | http://localhost:8000/api/docs/ |

---

## 🌍 Variáveis de ambiente

### Backend (`backend/.env`)

```env
# Django
SECRET_KEY=sua-secret-key-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Banco de dados
DATABASE_URL=postgresql://postgres:postgres@db:5432/obraflow

# Redis / Celery
REDIS_URL=redis://redis:6379/0

# Armazenamento
CLOUDFLARE_R2_ACCOUNT_ID=
CLOUDFLARE_R2_ACCESS_KEY=
CLOUDFLARE_R2_SECRET_KEY=
CLOUDFLARE_R2_BUCKET=

# Google Vision (OCR)
GOOGLE_VISION_API_KEY=

# E-mail (Resend)
RESEND_API_KEY=

# WhatsApp (Z-API)
ZAPI_INSTANCE_ID=
ZAPI_TOKEN=

# Nota Fiscal (NFE.io ou PlugNotas)
NFEIO_API_KEY=
```

### Frontend (`frontend/.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## 🧪 Testes

### Backend

```bash
docker compose exec backend pytest
```

### Frontend

```bash
npm run lint
npm run type-check
npm run build
```

---

## 📦 Deploy

### Frontend → Vercel

```bash
# Conecte o repositório no painel da Vercel
# Configure as variáveis de ambiente no painel
# Deploy automático a cada push na branch main
```

### Backend → Railway

```bash
# Conecte o repositório no painel do Railway
# Configure as variáveis de ambiente
# Railway detecta o Dockerfile automaticamente
```

---

## 🗺️ Roadmap

- [x] Estrutura inicial do projeto
- [ ] Autenticação e controle de perfis (admin, caixa, vendedor)
- [ ] Módulo de clientes com CEP automático
- [ ] Sistema de fiado completo
- [ ] Controle financeiro e caixa diário
- [ ] Controle de estoque
- [ ] OCR de boletos
- [ ] Integração WhatsApp (Z-API)
- [ ] Integração e-mail (Resend)
- [ ] Emissão de NF-e e NFS-e
- [ ] Dashboard com gráficos
- [ ] Modo multi-tenant (SaaS)

---

## 🤝 Contribuindo

Este projeto está em desenvolvimento ativo. Contribuições são bem-vindas!

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'feat: adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

<div align="center">
  <p>Feito para resolver problemas reais de quem trabalha com material de construção.</p>
</div>
