"""Selectors de leitura para Nota Fiscal de Entrada (sem regra de negócio)."""
from decimal import Decimal
from typing import Any

from django.db.models import Count, Q, QuerySet, Sum
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.estoque.models import MovimentacaoEstoque
from apps.financeiro.models import ContaPagar

from .models import HistoricoNotaFiscalEntrada, ItemNotaFiscalEntrada, NotaFiscalEntrada


def _require_company(user) -> None:
    if not getattr(user, "company_id", None):
        raise PermissionDenied("Usuário sem empresa associada.")


def _base_qs(company_id) -> QuerySet:
    return (
        NotaFiscalEntrada.objects
        .filter(company_id=company_id, deleted_at__isnull=True)
        .select_related("fornecedor", "conta_pagar", "criado_por", "confirmado_por", "rejeitado_por")
    )


def get_notas_visiveis(*, user) -> QuerySet:
    _require_company(user)
    return _base_qs(user.company_id)


def get_nota_by_id(*, user, nota_id) -> NotaFiscalEntrada:
    try:
        return get_notas_visiveis(user=user).get(pk=nota_id)
    except (NotaFiscalEntrada.DoesNotExist, ValueError, TypeError):
        raise NotFound("Nota fiscal não encontrada.")


def get_itens(*, user, nota_id) -> QuerySet:
    nota = get_nota_by_id(user=user, nota_id=nota_id)
    return (
        ItemNotaFiscalEntrada.objects
        .filter(company_id=nota.company_id, nota=nota, deleted_at__isnull=True)
        .select_related("produto", "movimentacao_estoque")
        .order_by("ordem")
    )


def get_item_by_id(*, user, nota_id, item_id) -> ItemNotaFiscalEntrada:
    itens = get_itens(user=user, nota_id=nota_id)
    try:
        return itens.get(pk=item_id)
    except (ItemNotaFiscalEntrada.DoesNotExist, ValueError, TypeError):
        raise NotFound("Item não encontrado.")


def get_historico(*, user, nota_id) -> QuerySet:
    nota = get_nota_by_id(user=user, nota_id=nota_id)
    return (
        HistoricoNotaFiscalEntrada.objects
        .filter(company_id=nota.company_id, nota=nota, deleted_at__isnull=True)
        .select_related("created_by")
        .order_by("-created_at")
    )


def get_dashboard(*, user) -> dict[str, Any]:
    _require_company(user)
    company_id = user.company_id
    qs = NotaFiscalEntrada.objects.filter(company_id=company_id, deleted_at__isnull=True)

    hoje = timezone.localdate()
    mes_inicio = hoje.replace(day=1)

    confirmadas_mes = qs.filter(
        status=NotaFiscalEntrada.STATUS_CONFIRMADA,
        confirmado_em__date__gte=mes_inicio,
    )
    rejeitadas_mes = qs.filter(
        status=NotaFiscalEntrada.STATUS_REJEITADA,
        rejeitado_em__date__gte=mes_inicio,
    )

    valor_importado = qs.filter(created_at__date__gte=mes_inicio).aggregate(
        total=Sum("valor_total")
    )["total"] or Decimal("0.00")

    valor_confirmado = confirmadas_mes.aggregate(
        total=Sum("valor_total")
    )["total"] or Decimal("0.00")

    # Movimentações geradas no mês
    movs_mes = MovimentacaoEstoque.objects.filter(
        company_id=company_id,
        deleted_at__isnull=True,
        tipo=MovimentacaoEstoque.TIPO_ENTRADA,
        created_at__date__gte=mes_inicio,
        item_nota_entrada__isnull=False,
    ).count()

    # Contas a pagar criadas via NF-e no mês
    contas_mes = NotaFiscalEntrada.objects.filter(
        company_id=company_id,
        deleted_at__isnull=True,
        conta_pagar__isnull=False,
        confirmado_em__date__gte=mes_inicio,
    ).count()

    # Fornecedores novos detectados (CNPJ não vinculado a Fornecedor)
    fornecedores_novos = qs.filter(
        fornecedor__isnull=True,
        fornecedor_cnpj_xml__gt="",
    ).values("fornecedor_cnpj_xml").distinct().count()

    # Itens sem produto pendentes (em notas aguardando revisão)
    itens_pendentes = ItemNotaFiscalEntrada.objects.filter(
        company_id=company_id,
        deleted_at__isnull=True,
        produto__isnull=True,
        ignorado=False,
        nota__status=NotaFiscalEntrada.STATUS_AGUARDANDO_REVISAO,
    ).count()

    return {
        "notas_importadas_hoje": qs.filter(created_at__date=hoje).count(),
        "aguardando_revisao": qs.filter(status=NotaFiscalEntrada.STATUS_AGUARDANDO_REVISAO).count(),
        "confirmadas_mes": confirmadas_mes.count(),
        "rejeitadas_mes": rejeitadas_mes.count(),
        "valor_total_importado_mes": valor_importado,
        "valor_total_confirmado_mes": valor_confirmado,
        "movimentacoes_estoque_geradas_mes": movs_mes,
        "contas_pagar_criadas_mes": contas_mes,
        "fornecedores_novos_detectados": fornecedores_novos,
        "itens_sem_produto_pendentes": itens_pendentes,
    }
