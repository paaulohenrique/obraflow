from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.exceptions import require_company
from apps.core.models import AuditLog
from apps.core.services import create_audit_log

from ..models import ConfiguracaoFinanceiraOperacional, ContaFinanceira, LancamentoFinanceiro


FORMA_CAMPO_CONTA = {
    LancamentoFinanceiro.FORMA_PIX: "conta_pix",
    LancamentoFinanceiro.FORMA_DINHEIRO: "conta_dinheiro",
    LancamentoFinanceiro.FORMA_CARTAO: "conta_cartao",
    LancamentoFinanceiro.FORMA_TRANSFERENCIA: "conta_transferencia",
}


def configuracao_financeira_snapshot(config: ConfiguracaoFinanceiraOperacional) -> dict[str, Any]:
    return {
        "id": str(config.pk),
        "company_id": str(config.company_id),
        "conta_pix_id": str(config.conta_pix_id) if config.conta_pix_id else None,
        "conta_dinheiro_id": str(config.conta_dinheiro_id) if config.conta_dinheiro_id else None,
        "conta_cartao_id": str(config.conta_cartao_id) if config.conta_cartao_id else None,
        "conta_transferencia_id": (
            str(config.conta_transferencia_id) if config.conta_transferencia_id else None
        ),
        "updated_by_id": str(config.updated_by_id) if config.updated_by_id else None,
    }


def _full_clean_or_400(obj) -> None:
    try:
        obj.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(getattr(exc, "message_dict", exc.messages))


def get_or_create_configuracao_financeira_operacional(*, company_id) -> ConfiguracaoFinanceiraOperacional:
    if company_id is None:
        raise PermissionDenied("Usuário sem empresa associada.")
    config, _ = ConfiguracaoFinanceiraOperacional.objects.select_related(
        "conta_pix",
        "conta_dinheiro",
        "conta_cartao",
        "conta_transferencia",
        "updated_by",
    ).get_or_create(company_id=company_id)
    return config


def _contas_ativas(*, company_id):
    return ContaFinanceira.objects.filter(
        company_id=company_id,
        ativo=True,
        is_active=True,
        deleted_at__isnull=True,
    )


def _preferida_por_nome(qs, termos: tuple[str, ...]) -> ContaFinanceira | None:
    if not termos:
        return None
    filtro = Q()
    for termo in termos:
        filtro |= Q(nome__icontains=termo) | Q(observacao__icontains=termo)
    return qs.filter(filtro).order_by("nome").first()


def _fallback_conta(*, company_id, forma_pagamento: str) -> ContaFinanceira | None:
    contas = _contas_ativas(company_id=company_id)
    if forma_pagamento == LancamentoFinanceiro.FORMA_DINHEIRO:
        return (
            _preferida_por_nome(contas.filter(tipo=ContaFinanceira.TIPO_CAIXA), ("principal", "caixa"))
            or contas.filter(tipo=ContaFinanceira.TIPO_CAIXA).order_by("nome").first()
        )
    if forma_pagamento == LancamentoFinanceiro.FORMA_PIX:
        return (
            _preferida_por_nome(contas, ("pix",))
            or contas.filter(tipo=ContaFinanceira.TIPO_BANCO).order_by("nome").first()
            or contas.order_by("nome").first()
        )
    if forma_pagamento == LancamentoFinanceiro.FORMA_CARTAO:
        return (
            _preferida_por_nome(contas, ("cartão", "cartao", "maquininha"))
            or contas.filter(tipo=ContaFinanceira.TIPO_BANCO).order_by("nome").first()
            or contas.order_by("nome").first()
        )
    if forma_pagamento == LancamentoFinanceiro.FORMA_TRANSFERENCIA:
        return (
            _preferida_por_nome(contas.filter(tipo=ContaFinanceira.TIPO_BANCO), ("banco", "corrente"))
            or contas.filter(tipo=ContaFinanceira.TIPO_BANCO).order_by("nome").first()
            or contas.order_by("nome").first()
        )
    return contas.order_by("nome").first()


def resolver_conta_operacional_pdv(*, company_id, forma_pagamento: str) -> ContaFinanceira | None:
    config = get_or_create_configuracao_financeira_operacional(company_id=company_id)
    campo = FORMA_CAMPO_CONTA.get(forma_pagamento)
    conta = getattr(config, campo, None) if campo else None
    if conta and conta.ativo and conta.is_active and conta.deleted_at is None:
        return conta
    return _fallback_conta(company_id=company_id, forma_pagamento=forma_pagamento)


def destinos_pdv(*, company_id) -> dict[str, ContaFinanceira | None]:
    return {
        forma: resolver_conta_operacional_pdv(company_id=company_id, forma_pagamento=forma)
        for forma in FORMA_CAMPO_CONTA
    }


@transaction.atomic
def atualizar_configuracao_financeira_operacional(
    *,
    user,
    config: ConfiguracaoFinanceiraOperacional,
    data: dict[str, Any],
    request=None,
) -> ConfiguracaoFinanceiraOperacional:
    require_company(user)
    if config.company_id != user.company_id:
        raise ValidationError({"configuracao": "Configuração não pertence à empresa."})

    config = ConfiguracaoFinanceiraOperacional.objects.select_for_update().get(
        pk=config.pk,
        company_id=user.company_id,
        deleted_at__isnull=True,
    )
    before = configuracao_financeira_snapshot(config)
    for field in FORMA_CAMPO_CONTA.values():
        if field in data:
            setattr(config, field, data[field])
    config.updated_by = user
    _full_clean_or_400(config)
    config.save(update_fields=[*FORMA_CAMPO_CONTA.values(), "updated_by", "updated_at"])

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_UPDATE,
        entity=config,
        before=before,
        after=configuracao_financeira_snapshot(config),
        request=request,
    )
    return config
