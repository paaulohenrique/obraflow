"""Matching automático de fornecedor e produto com dados extraídos da NF-e."""
from apps.empresas.validators import clean_cnpj


def match_fornecedor(*, cnpj_xml: str, company_id) -> "Fornecedor | None":
    """Busca Fornecedor ativo pelo CNPJ normalizado dentro da empresa."""
    from apps.estoque.models import Fornecedor

    cnpj = clean_cnpj(cnpj_xml or "")
    if not cnpj:
        return None
    return Fornecedor.objects.filter(
        company_id=company_id,
        cnpj=cnpj,
        deleted_at__isnull=True,
        is_active=True,
    ).first()


def match_produto_por_item(*, codigo_barras: str, codigo_fornecedor: str, company_id) -> "Produto | None":
    """Tenta vincular automaticamente produto ao item via match exato.

    Prioridade:
      1. codigo_barras (EAN) exato
      2. sku == codigo_fornecedor
    Retorna None se não encontrar.
    """
    from apps.estoque.models import Produto

    base_qs = Produto.objects.filter(
        company_id=company_id,
        deleted_at__isnull=True,
        is_active=True,
    )

    if codigo_barras:
        produto = base_qs.filter(codigo_barras=codigo_barras).first()
        if produto:
            return produto

    if codigo_fornecedor:
        produto = base_qs.filter(sku=codigo_fornecedor.upper()).first()
        if produto:
            return produto

    return None


def sugestoes_produto(*, descricao: str, company_id, limit: int = 5):
    """Retorna QuerySet de produtos sugeridos por similaridade de nome.

    Usa TrigramSimilarity do PostgreSQL quando disponível.
    Apenas sugestão — nunca auto-vincula.
    """
    from apps.estoque.models import Produto

    base_qs = Produto.objects.filter(
        company_id=company_id,
        deleted_at__isnull=True,
        is_active=True,
    )

    if not descricao:
        return base_qs.none()

    from django.db import connection, transaction as db_transaction

    try:
        from django.contrib.postgres.search import TrigramSimilarity
        with db_transaction.atomic():
            qs_trigram = (
                base_qs
                .annotate(similarity=TrigramSimilarity("nome", descricao))
                .filter(similarity__gt=0.15)
                .order_by("-similarity")[:limit]
            )
            return list(qs_trigram)
    except Exception:
        return list(base_qs.filter(nome__icontains=descricao[:30])[:limit])
