from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from apps.core.exceptions import require_company
from apps.core.models import AuditLog
from apps.core.services import create_audit_log

from ..models import FormaVendaProduto, Produto


def forma_venda_snapshot(forma: FormaVendaProduto) -> dict[str, Any]:
    return {
        "id": str(forma.pk),
        "company_id": str(forma.company_id),
        "produto_id": str(forma.produto_id),
        "nome": forma.nome,
        "codigo": forma.codigo,
        "unidade": forma.unidade,
        "fator_conversao": str(forma.fator_conversao),
        "preco_venda": str(forma.preco_venda),
        "ativo": forma.ativo,
        "padrao": forma.padrao,
        "permite_fracionado": forma.permite_fracionado,
    }


def _full_clean_or_400(obj) -> None:
    try:
        obj.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(getattr(exc, "message_dict", exc.messages))


def _locked_produto(*, produto_id, company_id) -> Produto:
    try:
        return (
            Produto.objects.select_for_update(of=("self",))
            .get(pk=produto_id, company_id=company_id, deleted_at__isnull=True)
        )
    except Produto.DoesNotExist:
        raise NotFound("Produto não encontrado.")


def converter_quantidade(*, forma_venda: FormaVendaProduto, quantidade: Decimal) -> Decimal:
    """Converte quantidade da forma de venda para a unidade base do produto."""
    if quantidade <= Decimal("0"):
        raise ValidationError({"quantidade": "Quantidade deve ser maior que zero."})
    return forma_venda.converter(quantidade)


@transaction.atomic
def criar_forma_venda(
    *,
    user,
    produto: Produto,
    data: dict[str, Any],
    request=None,
) -> FormaVendaProduto:
    require_company(user)
    company_id = user.company_id

    if produto.company_id != company_id:
        raise ValidationError({"produto": "Produto não pertence à empresa."})
    if not produto.is_active:
        raise ValidationError({"produto": "Produto inativo não pode receber formas de venda."})

    padrao = data.get("padrao", False)
    if padrao:
        _desativar_padrao_existente(produto_id=produto.pk, company_id=company_id)

    forma = FormaVendaProduto(
        company=user.company,
        produto=produto,
        nome=data["nome"],
        codigo=data.get("codigo", ""),
        unidade=data["unidade"],
        fator_conversao=data["fator_conversao"],
        preco_venda=data.get("preco_venda", Decimal("0.00")),
        ativo=data.get("ativo", True),
        padrao=padrao,
        permite_fracionado=data.get("permite_fracionado", True),
    )
    _full_clean_or_400(forma)
    forma.save()

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_CREATE,
        entity=forma,
        after=forma_venda_snapshot(forma),
        request=request,
    )
    return forma


@transaction.atomic
def atualizar_forma_venda(
    *,
    user,
    forma_venda: FormaVendaProduto,
    data: dict[str, Any],
    request=None,
) -> FormaVendaProduto:
    require_company(user)
    if forma_venda.company_id != user.company_id:
        raise ValidationError({"forma_venda": "Forma de venda não pertence à empresa."})

    before = forma_venda_snapshot(forma_venda)

    novo_padrao = data.get("padrao", forma_venda.padrao)
    if novo_padrao and not forma_venda.padrao:
        _desativar_padrao_existente(produto_id=forma_venda.produto_id, company_id=user.company_id)

    for field, value in data.items():
        setattr(forma_venda, field, value)

    _full_clean_or_400(forma_venda)
    forma_venda.save()

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=forma_venda,
        before=before,
        after=forma_venda_snapshot(forma_venda),
        request=request,
    )
    return forma_venda


@transaction.atomic
def definir_forma_padrao(
    *,
    user,
    forma_venda: FormaVendaProduto,
    request=None,
) -> FormaVendaProduto:
    require_company(user)
    if forma_venda.company_id != user.company_id:
        raise ValidationError({"forma_venda": "Forma de venda não pertence à empresa."})
    if not forma_venda.ativo:
        raise ValidationError({"forma_venda": "Forma de venda inativa não pode ser definida como padrão."})

    before = forma_venda_snapshot(forma_venda)
    _desativar_padrao_existente(produto_id=forma_venda.produto_id, company_id=user.company_id)

    forma_venda.padrao = True
    forma_venda.save(update_fields=["padrao", "updated_at"])

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=forma_venda,
        before=before,
        after=forma_venda_snapshot(forma_venda),
        request=request,
    )
    return forma_venda


@transaction.atomic
def inativar_forma_venda(
    *,
    user,
    forma_venda: FormaVendaProduto,
    request=None,
) -> FormaVendaProduto:
    require_company(user)
    if forma_venda.company_id != user.company_id:
        raise ValidationError({"forma_venda": "Forma de venda não pertence à empresa."})
    if not forma_venda.ativo:
        raise ValidationError({"forma_venda": "Forma de venda já está inativa."})
    if forma_venda.padrao:
        outras = FormaVendaProduto.objects.filter(
            company_id=user.company_id,
            produto_id=forma_venda.produto_id,
            ativo=True,
            deleted_at__isnull=True,
        ).exclude(pk=forma_venda.pk)
        if not outras.exists():
            raise ValidationError({
                "forma_venda": "Não é possível inativar a única forma de venda ativa do produto."
            })

    before = forma_venda_snapshot(forma_venda)
    forma_venda.ativo = False
    if forma_venda.padrao:
        forma_venda.padrao = False
    forma_venda.save(update_fields=["ativo", "padrao", "updated_at"])

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=forma_venda,
        before=before,
        after=forma_venda_snapshot(forma_venda),
        request=request,
    )
    return forma_venda


@transaction.atomic
def ativar_forma_venda(
    *,
    user,
    forma_venda: FormaVendaProduto,
    request=None,
) -> FormaVendaProduto:
    require_company(user)
    if forma_venda.company_id != user.company_id:
        raise ValidationError({"forma_venda": "Forma de venda não pertence à empresa."})
    if forma_venda.ativo:
        raise ValidationError({"forma_venda": "Forma de venda já está ativa."})

    before = forma_venda_snapshot(forma_venda)
    forma_venda.ativo = True
    forma_venda.save(update_fields=["ativo", "updated_at"])

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=forma_venda,
        before=before,
        after=forma_venda_snapshot(forma_venda),
        request=request,
    )
    return forma_venda


@transaction.atomic
def soft_delete_forma_venda(
    *,
    user,
    forma_venda: FormaVendaProduto,
    request=None,
) -> None:
    require_company(user)
    if forma_venda.company_id != user.company_id:
        raise ValidationError({"forma_venda": "Forma de venda não pertence à empresa."})

    ativas = FormaVendaProduto.objects.filter(
        company_id=user.company_id,
        produto_id=forma_venda.produto_id,
        ativo=True,
        deleted_at__isnull=True,
    ).exclude(pk=forma_venda.pk)
    if not ativas.exists():
        raise ValidationError({
            "forma_venda": "Não é possível remover a última forma de venda do produto."
        })

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_DELETE,
        entity=forma_venda,
        before=forma_venda_snapshot(forma_venda),
        request=request,
    )
    forma_venda.soft_delete()


def _desativar_padrao_existente(*, produto_id, company_id) -> None:
    FormaVendaProduto.objects.filter(
        company_id=company_id,
        produto_id=produto_id,
        padrao=True,
        ativo=True,
        deleted_at__isnull=True,
    ).update(padrao=False)
