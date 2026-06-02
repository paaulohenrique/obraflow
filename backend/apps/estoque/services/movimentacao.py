from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from apps.core.exceptions import require_company
from apps.core.models import AuditLog
from apps.core.services import create_audit_log
from apps.estoque.models import FormaVendaProduto, Fornecedor, MovimentacaoEstoque, Produto


def movimentacao_snapshot(movimentacao: MovimentacaoEstoque) -> dict[str, Any]:
    return {
        "id": str(movimentacao.pk),
        "company_id": str(movimentacao.company_id),
        "produto_id": str(movimentacao.produto_id),
        "tipo": movimentacao.tipo,
        "quantidade_delta": str(movimentacao.quantidade_delta),
        "estoque_antes": str(movimentacao.estoque_antes),
        "estoque_depois": str(movimentacao.estoque_depois),
        "custo_unitario": (
            str(movimentacao.custo_unitario) if movimentacao.custo_unitario is not None else None
        ),
        "valor_total": str(movimentacao.valor_total),
        "fornecedor_id": str(movimentacao.fornecedor_id) if movimentacao.fornecedor_id else None,
        "motivo": movimentacao.motivo,
        "observacao": movimentacao.observacao,
        "status": movimentacao.status,
        "created_by_id": str(movimentacao.created_by_id) if movimentacao.created_by_id else None,
        "movimentacao_cancelada_id": (
            str(movimentacao.movimentacao_cancelada_id)
            if movimentacao.movimentacao_cancelada_id
            else None
        ),
        "forma_venda_id": (
            str(movimentacao.forma_venda_id) if movimentacao.forma_venda_id else None
        ),
        "quantidade_informada": (
            str(movimentacao.quantidade_informada)
            if movimentacao.quantidade_informada is not None
            else None
        ),
        "idempotency_key": movimentacao.idempotency_key,
        "metadata": movimentacao.metadata,
    }


def _ensure_same_company(*, obj, company_id: Any, field: str) -> None:
    if obj and obj.company_id != company_id:
        raise ValidationError({field: "Objeto não pertence à empresa do usuário."})


def _full_clean_or_400(obj) -> None:
    try:
        obj.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(getattr(exc, "message_dict", exc.messages))


def _locked_produto(*, produto: Produto, company_id: Any) -> Produto:
    try:
        return (
            Produto.objects.select_for_update(of=("self",))
            .get(pk=produto.pk, company_id=company_id, deleted_at__isnull=True)
        )
    except Produto.DoesNotExist:
        raise NotFound("Produto não encontrado.")


def _check_idempotency(*, company_id: Any, idempotency_key: str) -> MovimentacaoEstoque | None:
    if not idempotency_key:
        return None
    return MovimentacaoEstoque.objects.filter(
        company_id=company_id,
        idempotency_key=idempotency_key,
        deleted_at__isnull=True,
    ).first()


def _valor_total(*, quantidade_delta: Decimal, custo_unitario: Decimal | None) -> Decimal:
    if custo_unitario is None:
        return Decimal("0.00")
    total = abs(quantidade_delta) * custo_unitario
    return total.quantize(Decimal("0.01"))


@transaction.atomic
def _registrar_movimentacao(
    *,
    user,
    produto: Produto,
    tipo: str,
    quantidade_delta: Decimal,
    custo_unitario: Decimal | None = None,
    fornecedor: Fornecedor | None = None,
    motivo: str = "",
    observacao: str = "",
    movimentacao_cancelada: MovimentacaoEstoque | None = None,
    forma_venda: FormaVendaProduto | None = None,
    quantidade_informada: Decimal | None = None,
    idempotency_key: str = "",
    metadata: dict[str, Any] | None = None,
    request=None,
) -> MovimentacaoEstoque:
    require_company(user)
    company_id = user.company_id
    idempotency_key = (idempotency_key or "").strip()

    existing = _check_idempotency(company_id=company_id, idempotency_key=idempotency_key)
    if existing:
        return existing

    _ensure_same_company(obj=produto, company_id=company_id, field="produto")
    _ensure_same_company(obj=fornecedor, company_id=company_id, field="fornecedor")
    _ensure_same_company(
        obj=movimentacao_cancelada,
        company_id=company_id,
        field="movimentacao_cancelada",
    )

    produto_locked = _locked_produto(produto=produto, company_id=company_id)
    if not produto_locked.is_active:
        raise ValidationError({"produto": "Produto inativo não pode ser movimentado."})

    if forma_venda is not None and forma_venda.company_id != company_id:
        raise ValidationError({"forma_venda": "Forma de venda não pertence à empresa."})
    if forma_venda is not None and forma_venda.produto_id != produto_locked.pk:
        raise ValidationError({"forma_venda": "Forma de venda não pertence a este produto."})
    if forma_venda is not None and not forma_venda.ativo:
        raise ValidationError({"forma_venda": "Forma de venda está inativa."})

    estoque_antes = produto_locked.estoque_atual
    estoque_depois = estoque_antes + quantidade_delta
    if estoque_depois < Decimal("0.000"):
        raise ValidationError({"estoque": "Estoque insuficiente para esta movimentação."})

    movimentacao = MovimentacaoEstoque(
        company=user.company,
        produto=produto_locked,
        tipo=tipo,
        quantidade_delta=quantidade_delta,
        estoque_antes=estoque_antes,
        estoque_depois=estoque_depois,
        custo_unitario=custo_unitario,
        valor_total=_valor_total(
            quantidade_delta=quantidade_delta,
            custo_unitario=custo_unitario,
        ),
        fornecedor=fornecedor,
        motivo=motivo,
        observacao=observacao,
        created_by=user,
        movimentacao_cancelada=movimentacao_cancelada,
        forma_venda=forma_venda,
        quantidade_informada=quantidade_informada,
        idempotency_key=idempotency_key,
        metadata=metadata or {},
    )
    _full_clean_or_400(movimentacao)
    movimentacao.save()

    produto_locked.estoque_atual = estoque_depois
    produto_locked.save(update_fields=["estoque_atual", "updated_at"])

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_CREATE,
        entity=movimentacao,
        after=movimentacao_snapshot(movimentacao),
        request=request,
    )
    return movimentacao


def entrada_estoque(
    *,
    user,
    produto: Produto,
    quantidade: Decimal,
    custo_unitario: Decimal | None = None,
    fornecedor: Fornecedor | None = None,
    motivo: str = "",
    observacao: str = "",
    forma_venda: FormaVendaProduto | None = None,
    quantidade_informada: Decimal | None = None,
    idempotency_key: str = "",
    metadata: dict[str, Any] | None = None,
    request=None,
) -> MovimentacaoEstoque:
    if forma_venda is not None and quantidade_informada is not None:
        quantidade = forma_venda.converter(quantidade_informada)
    if quantidade <= Decimal("0.000"):
        raise ValidationError({"quantidade": "Quantidade deve ser maior que zero."})
    return _registrar_movimentacao(
        user=user,
        produto=produto,
        tipo=MovimentacaoEstoque.TIPO_ENTRADA,
        quantidade_delta=quantidade,
        custo_unitario=custo_unitario,
        fornecedor=fornecedor,
        motivo=motivo,
        observacao=observacao,
        forma_venda=forma_venda,
        quantidade_informada=quantidade_informada,
        idempotency_key=idempotency_key,
        metadata=metadata,
        request=request,
    )


def saida_estoque(
    *,
    user,
    produto: Produto,
    quantidade: Decimal,
    motivo: str = "",
    observacao: str = "",
    forma_venda: FormaVendaProduto | None = None,
    quantidade_informada: Decimal | None = None,
    idempotency_key: str = "",
    metadata: dict[str, Any] | None = None,
    request=None,
) -> MovimentacaoEstoque:
    if forma_venda is not None and quantidade_informada is not None:
        quantidade = forma_venda.converter(quantidade_informada)
    if quantidade <= Decimal("0.000"):
        raise ValidationError({"quantidade": "Quantidade deve ser maior que zero."})
    return _registrar_movimentacao(
        user=user,
        produto=produto,
        tipo=MovimentacaoEstoque.TIPO_SAIDA,
        quantidade_delta=-quantidade,
        motivo=motivo,
        observacao=observacao,
        forma_venda=forma_venda,
        quantidade_informada=quantidade_informada,
        idempotency_key=idempotency_key,
        metadata=metadata,
        request=request,
    )


def ajuste_estoque(
    *,
    user,
    produto: Produto,
    quantidade_delta: Decimal,
    motivo: str,
    custo_unitario: Decimal | None = None,
    observacao: str = "",
    idempotency_key: str = "",
    metadata: dict[str, Any] | None = None,
    request=None,
) -> MovimentacaoEstoque:
    if quantidade_delta == Decimal("0.000"):
        raise ValidationError({"quantidade_delta": "Quantidade do ajuste não pode ser zero."})
    if not motivo:
        raise ValidationError({"motivo": "Motivo é obrigatório para ajuste."})
    return _registrar_movimentacao(
        user=user,
        produto=produto,
        tipo=MovimentacaoEstoque.TIPO_AJUSTE,
        quantidade_delta=quantidade_delta,
        custo_unitario=custo_unitario,
        motivo=motivo,
        observacao=observacao,
        idempotency_key=idempotency_key,
        metadata=metadata,
        request=request,
    )


def devolucao_estoque(
    *,
    user,
    produto: Produto,
    quantidade: Decimal,
    motivo: str,
    observacao: str = "",
    idempotency_key: str = "",
    metadata: dict[str, Any] | None = None,
    request=None,
) -> MovimentacaoEstoque:
    if quantidade <= Decimal("0.000"):
        raise ValidationError({"quantidade": "Quantidade deve ser maior que zero."})
    if not motivo:
        raise ValidationError({"motivo": "Motivo é obrigatório para devolução."})
    return _registrar_movimentacao(
        user=user,
        produto=produto,
        tipo=MovimentacaoEstoque.TIPO_DEVOLUCAO,
        quantidade_delta=quantidade,
        motivo=motivo,
        observacao=observacao,
        idempotency_key=idempotency_key,
        metadata=metadata,
        request=request,
    )


@transaction.atomic
def cancelar_movimentacao(
    *,
    user,
    movimentacao: MovimentacaoEstoque,
    motivo: str,
    observacao: str = "",
    idempotency_key: str = "",
    metadata: dict[str, Any] | None = None,
    request=None,
) -> MovimentacaoEstoque:
    require_company(user)
    if not motivo:
        raise ValidationError({"motivo": "Motivo é obrigatório para cancelamento."})

    company_id = user.company_id
    idempotency_key = (idempotency_key or "").strip()
    existing = _check_idempotency(company_id=company_id, idempotency_key=idempotency_key)
    if existing:
        return existing

    try:
        locked_movimentacao = (
            MovimentacaoEstoque.objects.select_for_update()
            .select_related("produto")
            .get(pk=movimentacao.pk, company_id=company_id, deleted_at__isnull=True)
        )
    except MovimentacaoEstoque.DoesNotExist:
        raise NotFound("Movimentação não encontrada.")

    if locked_movimentacao.status == MovimentacaoEstoque.STATUS_CANCELADA:
        raise ValidationError({"status": "Movimentação já foi cancelada."})
    if locked_movimentacao.tipo == MovimentacaoEstoque.TIPO_CANCELAMENTO:
        raise ValidationError({"tipo": "Movimentação de cancelamento não pode ser cancelada."})
    if locked_movimentacao.cancelamentos.exists():
        raise ValidationError({"movimentacao": "Movimentação já possui cancelamento."})

    before = movimentacao_snapshot(locked_movimentacao)
    cancelamento = _registrar_movimentacao(
        user=user,
        produto=locked_movimentacao.produto,
        tipo=MovimentacaoEstoque.TIPO_CANCELAMENTO,
        quantidade_delta=-locked_movimentacao.quantidade_delta,
        custo_unitario=locked_movimentacao.custo_unitario,
        fornecedor=locked_movimentacao.fornecedor,
        motivo=motivo,
        observacao=observacao,
        movimentacao_cancelada=locked_movimentacao,
        idempotency_key=idempotency_key,
        metadata=metadata,
        request=request,
    )

    locked_movimentacao.marcar_cancelada()
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=locked_movimentacao,
        before=before,
        after=movimentacao_snapshot(locked_movimentacao),
        request=request,
    )
    return cancelamento
