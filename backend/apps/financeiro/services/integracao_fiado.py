from django.db import transaction
from rest_framework.exceptions import ValidationError

from ..models import (
    CaixaDiario,
    CategoriaFinanceira,
    ContaFinanceira,
    LancamentoFinanceiro,
)
from .caixa import get_caixa_aberto
from .categoria import get_categoria_padrao
from .lancamento import cancelar_lancamento_financeiro, criar_lancamento_financeiro


def _default_conta_financeira(*, pagamento_fiado):
    company_id = pagamento_fiado.company_id
    forma = pagamento_fiado.forma_pagamento
    qs = ContaFinanceira.objects.filter(
        company_id=company_id,
        ativo=True,
        is_active=True,
        deleted_at__isnull=True,
    )
    if forma == LancamentoFinanceiro.FORMA_DINHEIRO:
        caixa = get_caixa_aberto(company_id=company_id, lock=False)
        if caixa:
            return caixa.conta_financeira
        return qs.filter(tipo=ContaFinanceira.TIPO_CAIXA).first()
    return (
        qs.filter(tipo=ContaFinanceira.TIPO_BANCO).first()
        or qs.filter(tipo=ContaFinanceira.TIPO_CARTEIRA).first()
        or qs.exclude(tipo=ContaFinanceira.TIPO_CAIXA).first()
    )


@transaction.atomic
def registrar_recebimento_fiado(
    pagamento_fiado,
    *,
    conta_financeira=None,
    user=None,
    request=None,
):
    actor = user or pagamento_fiado.created_by
    if actor is None:
        raise ValidationError({"user": "Usuário é obrigatório para integrar fiado ao financeiro."})
    conta = conta_financeira or _default_conta_financeira(pagamento_fiado=pagamento_fiado)
    if conta is None:
        raise ValidationError({
            "conta_financeira": "Conta financeira padrão não configurada para o recebimento."
        })

    categoria = get_categoria_padrao(
        company=pagamento_fiado.company,
        nome="Fiado",
        tipo=CategoriaFinanceira.TIPO_RECEITA,
    )
    if conta.tipo == ContaFinanceira.TIPO_CAIXA or pagamento_fiado.forma_pagamento == LancamentoFinanceiro.FORMA_DINHEIRO:
        caixa = get_caixa_aberto(
            company_id=pagamento_fiado.company_id,
            conta_financeira=conta,
            lock=True,
        )
        if caixa is None or caixa.status != CaixaDiario.STATUS_ABERTO:
            raise ValidationError({"caixa_diario": "Recebimento em dinheiro exige caixa aberto."})

    return criar_lancamento_financeiro(
        user=actor,
        conta_financeira=conta,
        categoria=categoria,
        tipo=LancamentoFinanceiro.TIPO_ENTRADA,
        valor=pagamento_fiado.valor,
        data_lancamento=pagamento_fiado.data_pagamento,
        descricao=f"Recebimento fiado {pagamento_fiado.conta_id}",
        origem_tipo=LancamentoFinanceiro.ORIGEM_FIADO,
        origem_id=pagamento_fiado.pk,
        forma_pagamento=pagamento_fiado.forma_pagamento,
        idempotency_key=f"fiado_pagamento:{pagamento_fiado.pk}",
        metadata={"pagamento_fiado_id": str(pagamento_fiado.pk)},
        request=request,
    )


@transaction.atomic
def estornar_recebimento_fiado(pagamento_fiado, *, user=None, request=None):
    actor = user or pagamento_fiado.cancelled_by or pagamento_fiado.created_by
    if actor is None:
        raise ValidationError({"user": "Usuário é obrigatório para estornar fiado no financeiro."})

    lancamento = (
        LancamentoFinanceiro.objects.filter(
            company_id=pagamento_fiado.company_id,
            origem_tipo=LancamentoFinanceiro.ORIGEM_FIADO,
            origem_id=pagamento_fiado.pk,
            deleted_at__isnull=True,
        )
        .select_related("conta_financeira", "categoria", "caixa_diario")
        .first()
    )
    if lancamento is None:
        raise ValidationError({"pagamento_fiado": "Recebimento financeiro do fiado não encontrado."})
    if lancamento.status == LancamentoFinanceiro.STATUS_CANCELADO:
        return lancamento.estornos.filter(deleted_at__isnull=True).first() or lancamento

    return cancelar_lancamento_financeiro(
        user=actor,
        lancamento=lancamento,
        motivo=pagamento_fiado.motivo_cancelamento or "Cancelamento do pagamento fiado.",
        idempotency_key=f"fiado_pagamento_cancelamento:{pagamento_fiado.pk}",
        request=request,
    )
