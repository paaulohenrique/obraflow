---
name: project-notas-entrada
description: Status e arquitetura do módulo Nota Fiscal de Entrada implementado na Sprint atual
metadata:
  type: project
---

Módulo `apps/notas_entrada` implementado e aprovado em testes (Sprint NF-e V1, 2026-05-31).

**Why:** Automatizar entrada de mercadorias via XML NF-e, eliminando lançamento manual no estoque.

**How to apply:** Módulo pronto para QA manual no Swagger. V2 implementará importação por chave de acesso (endpoint /importar-chave/ retorna 501 atualmente).

## Resultado Final
- 527 testes passando (era 417 antes)
- Cobertura global: 91.03% (era 90.52%)
- Cobertura do módulo: ~94%
- 0 migrations pendentes
- OpenAPI válido
- `manage.py check`: 0 issues

## Arquivos criados
- `apps/notas_entrada/models.py` — NotaFiscalEntrada, ItemNotaFiscalEntrada, HistoricoNotaFiscalEntrada
- `apps/notas_entrada/services/xml_parser.py` — parser NF-e com defusedxml (XXE-safe)
- `apps/notas_entrada/services/validators.py` — validação de arquivo XML (2MB, mime, sha256)
- `apps/notas_entrada/services/matching.py` — match fornecedor por CNPJ, produto por EAN/SKU
- `apps/notas_entrada/services/nota.py` — importar_xml_nota, vincular_fornecedor, vincular_produto_item, rejeitar_nota
- `apps/notas_entrada/services/confirmacao.py` — confirmar_nota (entrada_estoque + ContaPagar opcional)
- `apps/notas_entrada/selectors.py`, `filters.py`, `permissions.py`, `serializers.py`, `views.py`, `urls.py`
- `apps/notas_entrada/migrations/0001_initial.py`
- `requirements/base.txt` — adicionado defusedxml==0.7.1

## Endpoints disponíveis
```
GET    /api/v1/notas-entrada/
POST   /api/v1/notas-entrada/upload/
POST   /api/v1/notas-entrada/importar-chave/  [501 — V2]
GET    /api/v1/notas-entrada/{id}/
POST   /api/v1/notas-entrada/{id}/vincular-fornecedor/
POST   /api/v1/notas-entrada/{id}/confirmar/
POST   /api/v1/notas-entrada/{id}/rejeitar/
GET    /api/v1/notas-entrada/{id}/itens/
PATCH  /api/v1/notas-entrada/{id}/itens/{item_id}/
GET    /api/v1/notas-entrada/{id}/itens/{item_id}/sugestoes-produto/
GET    /api/v1/notas-entrada/{id}/historico/
GET    /api/v1/notas-entrada/dashboard/
```

## Riscos conhecidos
- pg_trgm não habilitado em prod → sugestões caem para icontains (sem impacto funcional)
- V2 pendente: importação por chave (SEFAZ/provedor externo)
- custo_medio do produto não atualizado na confirmação (decisão arquitetural V1)
