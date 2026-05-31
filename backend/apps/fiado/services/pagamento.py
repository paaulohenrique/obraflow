from typing import Any

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.core.exceptions import require_company
from apps.core.models import AuditLog
from apps.core.services import create_audit_log

from ..models import ContaFiado, HistoricoFiado, PagamentoFiado, ZERO_MONEY, money
from .conta import (
    _ensure_same_company,
    _full_clean_or_400,
    _locked_cliente,
    _locked_conta,
    _save_immutable_update,
    _save_model,
    cliente_snapshot,
    conta_snapshot,
    criar_historico_fiado,
    fechar_conta_se_quitada,
    pagamento_snapshot,
)


def _locked_pagamento(*, pagamento_id, company_id) -> PagamentoFiado:
    try:
        return (
            PagamentoFiado.objects.select_for_update(of=("self",))
            .select_related("conta", "created_by", "cancelled_by")
            .get(pk=pagamento_id, company_id=company_id, deleted_at__isnull=True)
        )
    except PagamentoFiado.DoesNotExist:
        raise NotFound("Pagamento fiado não encontrado.")


def _conta_cliente_id(*, conta_id, company_id):
    try:
        return ContaFiado.objects.only("cliente_id").get(
            pk=conta_id,
            company_id=company_id,
            deleted_at__isnull=True,
        ).cliente_id
    except ContaFiado.DoesNotExist:
        raise NotFound("Conta fiado não encontrada.")


def _existing_pagamento_by_key(*, company_id, idempotency_key: str) -> PagamentoFiado | None:
    if not idempotency_key:
        return None
    return (
        PagamentoFiado.objects.select_related("conta")
        .filter(
            company_id=company_id,
            idempotency_key=idempotency_key,
            deleted_at__isnull=True,
        )
        .first()
    )


def _update_data_ultimo_pagamento(cliente) -> None:
    ultimo = (
        PagamentoFiado.objects.filter(
            company_id=cliente.company_id,
            conta__cliente=cliente,
            status=PagamentoFiado.STATUS_CONFIRMADO,
            deleted_at__isnull=True,
        ).aggregate(max_data=Max("data_pagamento"))["max_data"]
    )
    cliente.data_ultimo_pagamento = (
        timezone.localtime(ultimo).date() if ultimo else None
    )


@transaction.atomic
def registrar_pagamento_fiado(
    *,
    user,
    conta: ContaFiado,
    data: dict[str, Any],
    request=None,
) -> PagamentoFiado:
    require_company(user)
    _ensure_same_company(obj=conta, company_id=user.company_id, field="conta")

    idempotency_key = (data.get("idempotency_key") or "").strip()
    existing = _existing_pagamento_by_key(
        company_id=user.company_id,
        idempotency_key=idempotency_key,
    )
    if existing:
        return existing

    cliente = _locked_cliente(cliente_id=conta.cliente_id, company_id=user.company_id)
    conta = _locked_conta(conta_id=conta.pk, company_id=user.company_id)
    if conta.cliente_id != cliente.pk:
        raise ValidationError({"conta": "Conta inconsistente com o cliente informado."})
    if conta.status != ContaFiado.STATUS_ABERTA:
        raise ValidationError({"status": "Somente conta aberta pode receber pagamento."})

    valor = money(data["valor"])
    if valor > conta.valor_restante:
        raise ValidationError({"valor": "Pagamento não pode ser maior que o valor restante."})
    if cliente.saldo_devedor < valor:
        raise ValidationError({"cliente": "Saldo devedor inconsistente para pagamento."})

    pagamento = PagamentoFiado(
        company=user.company,
        conta=conta,
        valor=valor,
        forma_pagamento=data["forma_pagamento"],
        data_pagamento=data.get("data_pagamento") or timezone.now(),
        observacao=data.get("observacao", ""),
        created_by=user,
        idempotency_key=idempotency_key,
        metadata=data.get("metadata") or {},
    )
    _full_clean_or_400(pagamento)
    pagamento.save()

    conta_before = conta_snapshot(conta)
    cliente_before = cliente_snapshot(cliente)

    conta.valor_pago = money(conta.valor_pago + valor)
    conta.valor_restante = money(conta.valor_total - conta.valor_pago)
    _save_model(conta, update_fields=["valor_pago", "valor_restante"])

    cliente.saldo_devedor = money(cliente.saldo_devedor - valor)
    cliente.data_ultimo_pagamento = timezone.localtime(pagamento.data_pagamento).date()
    cliente.save(update_fields=["saldo_devedor", "data_ultimo_pagamento", "updated_at"])

    pagamento_after = pagamento_snapshot(pagamento)
    conta_after = conta_snapshot(conta)
    cliente_after = cliente_snapshot(cliente)

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_CREATE,
        entity=pagamento,
        after=pagamento_after,
        request=request,
    )
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=conta,
        before=conta_before,
        after=conta_after,
        request=request,
    )
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=cliente,
        before=cliente_before,
        after=cliente_after,
        request=request,
    )
    criar_historico_fiado(
        user=user,
        conta=conta,
        pagamento=pagamento,
        evento=HistoricoFiado.EVENTO_PAGAMENTO_REGISTRADO,
        descricao="Pagamento registrado na conta fiado.",
        after=pagamento_after,
        metadata={"conta": conta_after, "cliente": cliente_after},
    )
    fechar_conta_se_quitada(user=user, conta=conta, request=request)
    return pagamento


@transaction.atomic
def cancelar_pagamento_fiado(
    *,
    user,
    pagamento: PagamentoFiado,
    motivo: str,
    observacao: str = "",
    request=None,
) -> PagamentoFiado:
    require_company(user)
    _ensure_same_company(obj=pagamento, company_id=user.company_id, field="pagamento")
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError({"motivo": "Motivo é obrigatório para cancelamento."})

    cliente_id = _conta_cliente_id(conta_id=pagamento.conta_id, company_id=user.company_id)
    cliente = _locked_cliente(cliente_id=cliente_id, company_id=user.company_id)
    conta = _locked_conta(conta_id=pagamento.conta_id, company_id=user.company_id)
    pagamento = _locked_pagamento(pagamento_id=pagamento.pk, company_id=user.company_id)

    if pagamento.conta_id != conta.pk or conta.cliente_id != cliente.pk:
        raise ValidationError({"pagamento": "Pagamento inconsistente com a conta informada."})
    if conta.status == ContaFiado.STATUS_CANCELADA:
        raise ValidationError({"status": "Conta cancelada não aceita cancelamento de pagamento."})
    if pagamento.status == PagamentoFiado.STATUS_CANCELADO:
        raise ValidationError({"status": "Pagamento fiado já está cancelado."})
    if conta.valor_pago < pagamento.valor:
        raise ValidationError({"valor_pago": "Total pago inconsistente para cancelamento."})

    pagamento_before = pagamento_snapshot(pagamento)
    conta_before = conta_snapshot(conta)
    cliente_before = cliente_snapshot(cliente)

    pagamento.status = PagamentoFiado.STATUS_CANCELADO
    pagamento.cancelled_by = user
    pagamento.cancelled_at = timezone.now()
    pagamento.motivo_cancelamento = motivo
    _save_immutable_update(
        pagamento,
        update_fields=["status", "cancelled_by", "cancelled_at", "motivo_cancelamento"],
    )

    conta.valor_pago = money(conta.valor_pago - pagamento.valor)
    conta.valor_restante = money(conta.valor_total - conta.valor_pago)
    update_fields = ["valor_pago", "valor_restante"]
    if conta.status == ContaFiado.STATUS_FECHADA:
        conta.status = ContaFiado.STATUS_ABERTA
        conta.data_fechamento = None
        conta.closed_by = None
        update_fields.extend(["status", "data_fechamento", "closed_by"])
    _save_model(conta, update_fields=update_fields)

    cliente.saldo_devedor = money(cliente.saldo_devedor + pagamento.valor)
    _update_data_ultimo_pagamento(cliente)
    cliente.save(update_fields=["saldo_devedor", "data_ultimo_pagamento", "updated_at"])

    pagamento_after = pagamento_snapshot(pagamento)
    conta_after = conta_snapshot(conta)
    cliente_after = cliente_snapshot(cliente)

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=pagamento,
        before=pagamento_before,
        after=pagamento_after,
        request=request,
    )
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=conta,
        before=conta_before,
        after=conta_after,
        request=request,
    )
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=cliente,
        before=cliente_before,
        after=cliente_after,
        request=request,
    )
    criar_historico_fiado(
        user=user,
        conta=conta,
        pagamento=pagamento,
        evento=HistoricoFiado.EVENTO_PAGAMENTO_CANCELADO,
        descricao="Pagamento da conta fiado cancelado.",
        before=pagamento_before,
        after=pagamento_after,
        metadata={"conta": conta_after, "cliente": cliente_after, "observacao": observacao},
    )
    return pagamento
