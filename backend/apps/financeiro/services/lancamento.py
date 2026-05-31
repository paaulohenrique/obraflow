from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.core.exceptions import require_company
from apps.core.models import AuditLog
from apps.core.services import create_audit_log

from ..models import (
    CaixaDiario,
    CategoriaFinanceira,
    ContaFinanceira,
    LancamentoFinanceiro,
    ZERO_MONEY,
    money,
)
from .categoria import _ensure_same_company, get_categoria_padrao
from .conta import _save_conta, conta_snapshot


def lancamento_snapshot(lancamento: LancamentoFinanceiro) -> dict[str, Any]:
    return {
        "id": str(lancamento.pk),
        "company_id": str(lancamento.company_id),
        "conta_financeira_id": str(lancamento.conta_financeira_id),
        "categoria_id": str(lancamento.categoria_id),
        "caixa_diario_id": str(lancamento.caixa_diario_id) if lancamento.caixa_diario_id else None,
        "tipo": lancamento.tipo,
        "valor": str(lancamento.valor),
        "data_lancamento": lancamento.data_lancamento.isoformat(),
        "descricao": lancamento.descricao,
        "origem_tipo": lancamento.origem_tipo,
        "origem_id": str(lancamento.origem_id) if lancamento.origem_id else None,
        "forma_pagamento": lancamento.forma_pagamento,
        "status": lancamento.status,
        "created_by_id": str(lancamento.created_by_id) if lancamento.created_by_id else None,
        "cancelled_by_id": str(lancamento.cancelled_by_id) if lancamento.cancelled_by_id else None,
        "cancelled_at": lancamento.cancelled_at.isoformat() if lancamento.cancelled_at else None,
        "motivo_cancelamento": lancamento.motivo_cancelamento,
        "estorno_de_id": str(lancamento.estorno_de_id) if lancamento.estorno_de_id else None,
        "idempotency_key": lancamento.idempotency_key,
        "metadata": lancamento.metadata,
    }


def _full_clean_or_400(obj) -> None:
    try:
        obj.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(getattr(exc, "message_dict", exc.messages))


def get_or_create_lancamento_idempotente(
    *,
    company_id,
    idempotency_key: str,
) -> LancamentoFinanceiro | None:
    idempotency_key = (idempotency_key or "").strip()
    if not idempotency_key:
        return None
    return (
        LancamentoFinanceiro.objects.select_related("conta_financeira", "categoria", "caixa_diario")
        .filter(
            company_id=company_id,
            idempotency_key=idempotency_key,
            deleted_at__isnull=True,
        )
        .first()
    )


def _locked_conta(conta: ContaFinanceira, company_id) -> ContaFinanceira:
    try:
        return ContaFinanceira.objects.select_for_update(of=("self",)).get(
            pk=conta.pk,
            company_id=company_id,
            deleted_at__isnull=True,
        )
    except ContaFinanceira.DoesNotExist:
        raise NotFound("Conta financeira não encontrada.")


def _locked_caixa_for_lancamento(
    *,
    company_id,
    conta: ContaFinanceira,
    caixa_diario: CaixaDiario | None,
) -> CaixaDiario | None:
    from .caixa import get_caixa_aberto

    if caixa_diario is not None:
        _ensure_same_company(obj=caixa_diario, company_id=company_id, field="caixa_diario")
        try:
            caixa = CaixaDiario.objects.select_for_update(of=("self",)).get(
                pk=caixa_diario.pk,
                company_id=company_id,
                deleted_at__isnull=True,
            )
        except CaixaDiario.DoesNotExist:
            raise NotFound("Caixa diário não encontrado.")
    else:
        caixa = get_caixa_aberto(company_id=company_id, conta_financeira=conta, lock=True)

    if caixa is None:
        raise ValidationError({"caixa_diario": "Conta caixa exige caixa aberto."})
    if caixa.status != CaixaDiario.STATUS_ABERTO:
        raise ValidationError({"caixa_diario": "Caixa fechado não recebe lançamento."})
    if caixa.conta_financeira_id != conta.pk:
        raise ValidationError({"caixa_diario": "Caixa não pertence à conta financeira informada."})
    return caixa


def _validate_lancamento_inputs(
    *,
    company_id,
    conta: ContaFinanceira,
    categoria: CategoriaFinanceira,
    tipo: str,
    valor: Decimal,
    forma_pagamento: str,
) -> None:
    _ensure_same_company(obj=conta, company_id=company_id, field="conta_financeira")
    _ensure_same_company(obj=categoria, company_id=company_id, field="categoria")
    if not conta.ativo or not conta.is_active:
        raise ValidationError({"conta_financeira": "Conta financeira inativa."})
    if not categoria.ativa or not categoria.is_active:
        raise ValidationError({"categoria": "Categoria financeira inativa."})
    if tipo == LancamentoFinanceiro.TIPO_ENTRADA and categoria.tipo != CategoriaFinanceira.TIPO_RECEITA:
        raise ValidationError({"categoria": "Entrada exige categoria de receita."})
    if tipo == LancamentoFinanceiro.TIPO_SAIDA and categoria.tipo != CategoriaFinanceira.TIPO_DESPESA:
        raise ValidationError({"categoria": "Saída exige categoria de despesa."})
    if money(valor) <= ZERO_MONEY:
        raise ValidationError({"valor": "Valor deve ser maior que zero."})
    if forma_pagamento == LancamentoFinanceiro.FORMA_DINHEIRO and conta.tipo != ContaFinanceira.TIPO_CAIXA:
        raise ValidationError({"conta_financeira": "Pagamento em dinheiro exige conta tipo CAIXA."})


def _apply_saldo(conta: ContaFinanceira, *, tipo: str, valor: Decimal) -> None:
    before = money(conta.saldo_atual)
    if tipo == LancamentoFinanceiro.TIPO_ENTRADA:
        conta.saldo_atual = money(before + valor)
    else:
        depois = money(before - valor)
        if depois < ZERO_MONEY:
            raise ValidationError({"saldo_atual": "Saída não pode deixar a conta negativa."})
        conta.saldo_atual = depois


def _recalcular_caixa_se_aberto(*, caixa: CaixaDiario | None) -> None:
    if caixa is None or caixa.status != CaixaDiario.STATUS_ABERTO:
        return
    from .caixa import _save_caixa, recalcular_totais_caixa

    recalcular_totais_caixa(caixa)
    _save_caixa(
        caixa,
        update_fields=["total_entradas", "total_saidas", "saldo_final"],
    )


@transaction.atomic
def criar_lancamento_financeiro(
    *,
    user,
    conta_financeira: ContaFinanceira,
    categoria: CategoriaFinanceira,
    tipo: str,
    valor: Decimal,
    data_lancamento=None,
    descricao: str = "",
    origem_tipo: str = LancamentoFinanceiro.ORIGEM_MANUAL,
    origem_id=None,
    forma_pagamento: str = LancamentoFinanceiro.FORMA_OUTRO,
    caixa_diario: CaixaDiario | None = None,
    estorno_de: LancamentoFinanceiro | None = None,
    idempotency_key: str = "",
    metadata: dict[str, Any] | None = None,
    request=None,
) -> LancamentoFinanceiro:
    require_company(user)
    idempotency_key = (idempotency_key or "").strip()
    existing = get_or_create_lancamento_idempotente(
        company_id=user.company_id,
        idempotency_key=idempotency_key,
    )
    if existing:
        return existing

    conta = _locked_conta(conta_financeira, user.company_id)
    _validate_lancamento_inputs(
        company_id=user.company_id,
        conta=conta,
        categoria=categoria,
        tipo=tipo,
        valor=valor,
        forma_pagamento=forma_pagamento,
    )

    caixa = None
    if conta.tipo == ContaFinanceira.TIPO_CAIXA or forma_pagamento == LancamentoFinanceiro.FORMA_DINHEIRO:
        caixa = _locked_caixa_for_lancamento(
            company_id=user.company_id,
            conta=conta,
            caixa_diario=caixa_diario,
        )

    conta_before = conta_snapshot(conta)
    valor = money(valor)
    _apply_saldo(conta, tipo=tipo, valor=valor)

    lancamento = LancamentoFinanceiro(
        company=user.company,
        conta_financeira=conta,
        categoria=categoria,
        caixa_diario=caixa,
        tipo=tipo,
        valor=valor,
        data_lancamento=data_lancamento or timezone.now(),
        descricao=descricao,
        origem_tipo=origem_tipo,
        origem_id=origem_id,
        forma_pagamento=forma_pagamento,
        status=LancamentoFinanceiro.STATUS_CONFIRMADO,
        created_by=user,
        estorno_de=estorno_de,
        idempotency_key=idempotency_key,
        metadata=metadata or {},
    )
    _full_clean_or_400(lancamento)

    try:
        lancamento.save()
    except IntegrityError:
        existing = get_or_create_lancamento_idempotente(
            company_id=user.company_id,
            idempotency_key=idempotency_key,
        )
        if existing:
            return existing
        raise

    _save_conta(conta, update_fields=["saldo_atual"])
    _recalcular_caixa_se_aberto(caixa=caixa)

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_CREATE,
        entity=lancamento,
        after=lancamento_snapshot(lancamento),
        request=request,
    )
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=conta,
        before=conta_before,
        after=conta_snapshot(conta),
        request=request,
    )
    return lancamento


def _categoria_estorno(*, user, original: LancamentoFinanceiro) -> CategoriaFinanceira:
    if original.tipo == LancamentoFinanceiro.TIPO_ENTRADA:
        return get_categoria_padrao(
            company=user.company,
            nome="Estorno de Receita",
            tipo=CategoriaFinanceira.TIPO_DESPESA,
        )
    return get_categoria_padrao(
        company=user.company,
        nome="Estorno de Despesa",
        tipo=CategoriaFinanceira.TIPO_RECEITA,
    )


@transaction.atomic
def cancelar_lancamento_financeiro(
    *,
    user,
    lancamento: LancamentoFinanceiro,
    motivo: str,
    idempotency_key: str = "",
    request=None,
) -> LancamentoFinanceiro:
    require_company(user)
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError({"motivo": "Motivo é obrigatório para cancelamento."})
    _ensure_same_company(obj=lancamento, company_id=user.company_id, field="lancamento")

    try:
        original = (
            LancamentoFinanceiro.objects.select_for_update(of=("self",))
            .select_related("conta_financeira", "categoria", "caixa_diario")
            .get(pk=lancamento.pk, company_id=user.company_id, deleted_at__isnull=True)
        )
    except LancamentoFinanceiro.DoesNotExist:
        raise NotFound("Lançamento financeiro não encontrado.")

    existing_estorno = original.estornos.filter(deleted_at__isnull=True).first()
    if original.status == LancamentoFinanceiro.STATUS_CANCELADO:
        existing_by_key = get_or_create_lancamento_idempotente(
            company_id=user.company_id,
            idempotency_key=idempotency_key,
        )
        if existing_by_key:
            return existing_by_key
        raise ValidationError({"status": "Lançamento já está cancelado."})
    if original.origem_tipo == LancamentoFinanceiro.ORIGEM_ESTORNO:
        raise ValidationError({"origem_tipo": "Lançamento de estorno não pode ser cancelado."})
    if existing_estorno:
        raise ValidationError({"lancamento": "Lançamento já possui estorno."})

    original_before = lancamento_snapshot(original)
    reverse_tipo = (
        LancamentoFinanceiro.TIPO_SAIDA
        if original.tipo == LancamentoFinanceiro.TIPO_ENTRADA
        else LancamentoFinanceiro.TIPO_ENTRADA
    )
    reverse_key = (idempotency_key or f"estorno:{original.pk}").strip()
    estorno = criar_lancamento_financeiro(
        user=user,
        conta_financeira=original.conta_financeira,
        categoria=_categoria_estorno(user=user, original=original),
        tipo=reverse_tipo,
        valor=original.valor,
        data_lancamento=timezone.now(),
        descricao=f"Estorno: {original.descricao or original.pk}",
        origem_tipo=LancamentoFinanceiro.ORIGEM_ESTORNO,
        origem_id=original.pk,
        forma_pagamento=original.forma_pagamento,
        estorno_de=original,
        idempotency_key=reverse_key,
        metadata={"motivo": motivo, "original_id": str(original.pk)},
        request=request,
    )

    original.status = LancamentoFinanceiro.STATUS_CANCELADO
    original.cancelled_by = user
    original.cancelled_at = timezone.now()
    original.motivo_cancelamento = motivo
    original._allow_update = True
    original.full_clean()
    original.save(
        update_fields=[
            "status",
            "cancelled_by",
            "cancelled_at",
            "motivo_cancelamento",
            "updated_at",
        ]
    )
    original._allow_update = False

    if original.caixa_diario_id and original.caixa_diario.status == CaixaDiario.STATUS_ABERTO:
        _recalcular_caixa_se_aberto(caixa=original.caixa_diario)

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=original,
        before=original_before,
        after=lancamento_snapshot(original),
        request=request,
    )
    return estorno
