"""Service de confirmação de Nota Fiscal de Entrada.

Orquestra a entrada no estoque e criação opcional de ContaPagar,
dentro de uma única transação atômica.
"""
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.core.exceptions import require_company
from apps.core.models import AuditLog
from apps.core.services import create_audit_log
from apps.estoque.services.movimentacao import entrada_estoque
from apps.financeiro.services.conta_pagar import criar_conta_pagar

from ..models import HistoricoNotaFiscalEntrada, ItemNotaFiscalEntrada, NotaFiscalEntrada
from .nota import criar_historico, nota_snapshot


def _full_clean_or_400(obj) -> None:
    try:
        obj.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(getattr(exc, "message_dict", exc.messages))


def _locked_nota(*, nota_id, company_id) -> NotaFiscalEntrada:
    try:
        return (
            NotaFiscalEntrada.objects
            .select_for_update(of=("self",))
            .select_related("company", "fornecedor", "criado_por")
            .get(pk=nota_id, company_id=company_id, deleted_at__isnull=True)
        )
    except NotaFiscalEntrada.DoesNotExist:
        raise NotFound("Nota fiscal não encontrada.")


def _itens_pendentes(nota: NotaFiscalEntrada) -> list[ItemNotaFiscalEntrada]:
    """Retorna itens sem produto E sem ignorado=True."""
    return list(
        ItemNotaFiscalEntrada.objects.filter(
            nota=nota,
            produto__isnull=True,
            ignorado=False,
            deleted_at__isnull=True,
        )
    )


def _itens_ativos(nota: NotaFiscalEntrada):
    return ItemNotaFiscalEntrada.objects.filter(
        nota=nota,
        produto__isnull=False,
        ignorado=False,
        deleted_at__isnull=True,
    ).select_related("produto", "produto__fornecedor_principal", "forma_venda")


@transaction.atomic
def confirmar_nota(
    *,
    user,
    nota_id,
    criar_conta_pagar_flag: bool = False,
    dados_conta_pagar: dict[str, Any] | None = None,
    request=None,
) -> NotaFiscalEntrada:
    """Confirma uma NF-e: cria movimentações de estoque e ContaPagar opcional.

    Garantias:
    - select_for_update previne confirmação simultânea
    - transaction.atomic garante rollback total em qualquer falha
    - idempotência via status: nota já CONFIRMADA retorna 200 sem reprocessar
    """
    require_company(user)
    company_id = user.company_id

    nota = _locked_nota(nota_id=nota_id, company_id=company_id)

    # Idempotência: já confirmada, retorna sem reprocessar
    if nota.status == NotaFiscalEntrada.STATUS_CONFIRMADA:
        return nota

    if nota.status != NotaFiscalEntrada.STATUS_AGUARDANDO_REVISAO:
        raise ValidationError({"status": "Apenas notas aguardando revisão podem ser confirmadas."})

    # Verificar itens pendentes
    pendentes = _itens_pendentes(nota)
    if pendentes:
        raise ValidationError({
            "itens": (
                f"{len(pendentes)} item(ns) sem produto vinculado e não marcado(s) como ignorado. "
                f"Vincule o produto ou marque como ignorado antes de confirmar."
            )
        })

    # Validar dados de ContaPagar se solicitado
    if criar_conta_pagar_flag:
        if not dados_conta_pagar or not dados_conta_pagar.get("categoria"):
            raise ValidationError({"dados_conta_pagar": "Categoria é obrigatória para criar Conta a Pagar."})
        if not dados_conta_pagar.get("data_vencimento"):
            raise ValidationError({"dados_conta_pagar": "Data de vencimento é obrigatória para criar Conta a Pagar."})

    before = nota_snapshot(nota)
    itens_ativos = list(_itens_ativos(nota))

    # Criar MovimentacaoEstoque para cada item ativo
    for item in itens_ativos:
        custo = item.custo_unitario or item.valor_unitario

        # Converte para unidade base quando forma_venda está definida.
        # item.quantidade = qtd bruta do XML (ex: 10 sacos).
        # qtd_base = qtd na unidade base do produto (ex: 500 kg).
        if item.forma_venda_id:
            qtd_base = item.forma_venda.converter(item.quantidade)
            qtd_informada = item.quantidade  # preserva qtd original do XML
        else:
            qtd_base = item.quantidade
            qtd_informada = None

        idem_key = f"nfe-item-{item.pk}"
        movimentacao = entrada_estoque(
            user=user,
            produto=item.produto,
            quantidade=qtd_base,
            custo_unitario=Decimal(str(custo)) if custo else None,
            fornecedor=nota.fornecedor,
            motivo=f"NF-e {nota.numero}/{nota.serie}",
            observacao=f"Item: {item.descricao_original[:200]}",
            forma_venda=item.forma_venda,
            quantidade_informada=qtd_informada,
            idempotency_key=idem_key,
            metadata={
                "nota_id": str(nota.pk),
                "item_id": str(item.pk),
                "nota_numero": nota.numero,
            },
            request=request,
        )
        # Atualizar item com a movimentação criada (save direto — item não confirmado ainda)
        item.movimentacao_estoque = movimentacao
        item.save(update_fields=["movimentacao_estoque", "updated_at"])

        criar_historico(
            nota=nota,
            evento=HistoricoNotaFiscalEntrada.EVENTO_ENTRADA_ESTOQUE_CRIADA,
            descricao=f"Entrada de estoque criada para '{item.descricao_original}'.",
            user=user,
            metadata={
                "item_id": str(item.pk),
                "produto_id": str(item.produto_id),
                "movimentacao_id": str(movimentacao.pk),
                "quantidade": str(item.quantidade),
            },
            request=request,
        )

    # Criar ContaPagar se solicitado
    if criar_conta_pagar_flag and nota.conta_pagar_id is None:
        conta = criar_conta_pagar(
            user=user,
            data={
                "fornecedor": nota.fornecedor,
                "descricao": f"NF-e {nota.numero}/{nota.serie} — {nota.fornecedor_nome_xml}",
                "categoria": dados_conta_pagar["categoria"],
                "valor_total": nota.valor_total,
                "data_emissao": nota.data_emissao,
                "data_vencimento": dados_conta_pagar["data_vencimento"],
                "observacao": dados_conta_pagar.get("observacao", ""),
            },
            request=request,
        )
        nota.conta_pagar = conta
        criar_historico(
            nota=nota,
            evento=HistoricoNotaFiscalEntrada.EVENTO_CONTA_PAGAR_CRIADA,
            descricao=f"Conta a pagar criada: R$ {nota.valor_total}.",
            user=user,
            metadata={"conta_pagar_id": str(conta.pk)},
            request=request,
        )

    # Confirmar nota
    nota.status = NotaFiscalEntrada.STATUS_CONFIRMADA
    nota.confirmado_por = user
    nota.confirmado_em = timezone.now()
    nota._allow_update = True
    try:
        _full_clean_or_400(nota)
        nota.save(update_fields=[
            "status", "confirmado_por", "confirmado_em", "conta_pagar", "updated_at"
        ])
    finally:
        nota._allow_update = False

    after = nota_snapshot(nota)
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=nota,
        before=before,
        after=after,
        request=request,
    )
    criar_historico(
        nota=nota,
        evento=HistoricoNotaFiscalEntrada.EVENTO_CONFIRMADA,
        descricao=f"Nota confirmada. {len(itens_ativos)} item(ns) lançados no estoque.",
        user=user,
        before=before,
        after=after,
        metadata={
            "itens_confirmados": len(itens_ativos),
            "conta_pagar_criada": criar_conta_pagar_flag and nota.conta_pagar_id is not None,
        },
        request=request,
    )

    return nota
