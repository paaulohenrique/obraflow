"""Helpers para montar componentes de template WhatsApp."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.notificacoes.models import Notificacao


def _body_params(*values: str) -> dict:
    return {
        "type": "body",
        "parameters": [{"type": "text", "text": str(v)} for v in values],
    }


def componentes_cobranca_fiado(
    *,
    cliente_nome: str,
    valor_restante: Decimal,
    data_vencimento: str,
) -> list[dict[str, Any]]:
    return [_body_params(cliente_nome, f"{valor_restante:.2f}", data_vencimento)]


def componentes_lembrete_vencimento(
    *,
    cliente_nome: str,
    valor_restante: Decimal,
    data_vencimento: str,
    dias_restantes: int,
) -> list[dict[str, Any]]:
    return [
        _body_params(
            cliente_nome,
            f"{valor_restante:.2f}",
            data_vencimento,
            str(dias_restantes),
        )
    ]


def componentes_confirmacao_pagamento(
    *,
    cliente_nome: str,
    valor: Decimal,
) -> list[dict[str, Any]]:
    return [_body_params(cliente_nome, f"{valor:.2f}")]


def componentes_resumo_conta(
    *,
    cliente_nome: str,
    valor_total: Decimal,
    valor_pago: Decimal,
    valor_restante: Decimal,
) -> list[dict[str, Any]]:
    return [
        _body_params(
            cliente_nome,
            f"{valor_total:.2f}",
            f"{valor_pago:.2f}",
            f"{valor_restante:.2f}",
        )
    ]


def _get_componentes(notificacao: "Notificacao") -> list[dict[str, Any]]:
    """Recupera componentes pré-computados do payload ou retorna lista vazia."""
    return notificacao.payload.get("componentes", [])
