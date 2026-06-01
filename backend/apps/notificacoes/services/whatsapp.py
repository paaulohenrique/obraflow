"""Business services para envio de notificações WhatsApp."""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from apps.notificacoes.models import (
    CanalNotificacao,
    Notificacao,
    TemplateNotificacao,
    normalizar_telefone,
)

logger = logging.getLogger("apps.notificacoes")

_RATE_LIMIT_PER_MINUTE = 30
_RATE_WINDOW = 60


class NotificacaoError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _canal_whatsapp_ativo(company_id) -> CanalNotificacao:
    canal = (
        CanalNotificacao.objects.filter(
            company_id=company_id,
            tipo=CanalNotificacao.TIPO_WHATSAPP,
            ativo=True,
            deleted_at__isnull=True,
        )
        .first()
    )
    if not canal:
        raise NotificacaoError(
            "CANAL_INDISPONIVEL",
            "Não há canal WhatsApp ativo configurado para esta empresa.",
        )
    return canal


def _template_ativo(company_id, tipo: str, canal: CanalNotificacao) -> TemplateNotificacao | None:
    return TemplateNotificacao.objects.filter(
        company_id=company_id,
        tipo=tipo,
        canal=canal,
        ativo=True,
        deleted_at__isnull=True,
    ).first()


def _verificar_rate_limit(company_id) -> None:
    key = f"notif_wpp_rate:{company_id}"
    count = cache.get(key, 0)
    if count >= _RATE_LIMIT_PER_MINUTE:
        raise NotificacaoError(
            "RATE_LIMIT",
            f"Limite de {_RATE_LIMIT_PER_MINUTE} mensagens/minuto atingido.",
        )
    pipe = cache.get_or_set(key, 0, _RATE_WINDOW)
    cache.incr(key)


def _verificar_duplicata(
    *,
    company_id,
    origem_tipo: str,
    origem_id,
    tipo: str,
) -> bool:
    """True se já existe notificação bem-sucedida para essa origem."""
    return Notificacao.objects.filter(
        company_id=company_id,
        origem_tipo=origem_tipo,
        origem_id=origem_id,
        tipo=tipo,
        status__in=list(Notificacao.TERMINAL_STATUSES),
    ).exists()


def criar_notificacao(
    *,
    company_id,
    tipo: str,
    destinatario_nome: str,
    destinatario_contato: str,
    mensagem: str = "",
    payload: dict[str, Any] | None = None,
    origem_tipo: str = "",
    origem_id=None,
    idempotency_key: str = "",
    created_by=None,
    scheduled_at=None,
) -> Notificacao:
    """Cria uma Notificação PENDENTE. Não envia — use a task Celery."""
    canal = _canal_whatsapp_ativo(company_id)
    template = _template_ativo(company_id, tipo, canal)

    telefone = normalizar_telefone(destinatario_contato)

    if idempotency_key:
        existente = Notificacao.objects.filter(
            company_id=company_id,
            idempotency_key=idempotency_key,
            deleted_at__isnull=True,
        ).first()
        if existente:
            return existente

    notificacao = Notificacao.objects.create(
        company_id=company_id,
        canal=canal,
        template=template,
        tipo=tipo,
        destinatario_nome=destinatario_nome,
        destinatario_contato=telefone,
        mensagem=mensagem,
        payload=payload or {},
        status=Notificacao.STATUS_PENDENTE,
        origem_tipo=origem_tipo,
        origem_id=origem_id,
        idempotency_key=idempotency_key,
        scheduled_at=scheduled_at,
        created_by=created_by,
    )
    return notificacao


def executar_envio(
    *,
    notificacao: Notificacao,
    provider=None,
) -> Notificacao:
    """Executa o envio real via provider. Chamado pela task Celery."""
    from .providers import get_whatsapp_provider, WhatsAppError

    if notificacao.ja_enviada:
        return notificacao

    _verificar_rate_limit(notificacao.company_id)

    if provider is None:
        provider = get_whatsapp_provider()

    notificacao.status = Notificacao.STATUS_ENFILEIRADA
    notificacao.save(update_fields=["status", "updated_at"])

    try:
        if notificacao.template and notificacao.template.provider_template_name:
            from .templates import _get_componentes
            components = _get_componentes(notificacao)
            result = provider.send_template_message(
                to=notificacao.destinatario_contato,
                template_name=notificacao.template.provider_template_name,
                language_code=notificacao.template.linguagem,
                components=components,
            )
        else:
            result = provider.send_text_message(
                to=notificacao.destinatario_contato,
                body=notificacao.mensagem,
            )
    except WhatsAppError as exc:
        notificacao.status = Notificacao.STATUS_FALHOU
        notificacao.erro_codigo = exc.code
        notificacao.erro_mensagem = exc.message
        notificacao.failed_at = timezone.now()
        notificacao.save(
            update_fields=["status", "erro_codigo", "erro_mensagem", "failed_at", "updated_at"]
        )
        logger.error(
            "Notificacao %s falhou: [%s] %s",
            notificacao.pk,
            exc.code,
            exc.message,
        )
        raise

    notificacao.status = Notificacao.STATUS_ENVIADA
    notificacao.provider_message_id = result.message_id
    notificacao.sent_at = timezone.now()
    notificacao.save(
        update_fields=["status", "provider_message_id", "sent_at", "updated_at"]
    )
    logger.info(
        "Notificacao %s enviada wamid=%s",
        notificacao.pk,
        result.message_id,
    )
    return notificacao


# ---- Casos de uso ----


def enviar_cobranca_fiado(
    *,
    conta_fiado_id,
    created_by=None,
    provider=None,
) -> Notificacao:
    from apps.fiado.models import ContaFiado
    from .templates import componentes_cobranca_fiado

    conta = ContaFiado.objects.select_related("cliente", "company").get(pk=conta_fiado_id)

    tipo = Notificacao.TIPO_COBRANCA_FIADO
    idem_key = f"cobranca_fiado:{conta_fiado_id}"

    if _verificar_duplicata(
        company_id=conta.company_id,
        origem_tipo="ContaFiado",
        origem_id=conta.pk,
        tipo=tipo,
    ):
        return Notificacao.objects.filter(
            company_id=conta.company_id,
            origem_tipo="ContaFiado",
            origem_id=conta.pk,
            tipo=tipo,
        ).latest("created_at")

    cliente = conta.cliente
    telefone = getattr(cliente, "telefone", None) or ""
    if not telefone:
        raise NotificacaoError(
            "SEM_TELEFONE",
            f"Cliente {cliente.pk} não possui telefone cadastrado.",
        )

    data_venc = (
        conta.data_vencimento.strftime("%d/%m/%Y") if conta.data_vencimento else "—"
    )

    mensagem = (
        f"Olá {cliente.nome}, sua conta fiado possui saldo de "
        f"R$ {conta.valor_restante:.2f} com vencimento em {data_venc}."
    )

    payload = {
        "valor_restante": str(conta.valor_restante),
        "data_vencimento": data_venc,
        "componentes": componentes_cobranca_fiado(
            cliente_nome=cliente.nome,
            valor_restante=conta.valor_restante,
            data_vencimento=data_venc,
        ),
    }

    notificacao = criar_notificacao(
        company_id=conta.company_id,
        tipo=tipo,
        destinatario_nome=cliente.nome,
        destinatario_contato=telefone,
        mensagem=mensagem,
        payload=payload,
        origem_tipo="ContaFiado",
        origem_id=conta.pk,
        idempotency_key=idem_key,
        created_by=created_by,
    )

    notificacao.payload["componentes"] = payload["componentes"]
    notificacao.save(update_fields=["payload", "updated_at"])

    return notificacao


def enviar_confirmacao_pagamento(
    *,
    pagamento_fiado_id,
    created_by=None,
    provider=None,
) -> Notificacao:
    from apps.fiado.models import PagamentoFiado
    from .templates import componentes_confirmacao_pagamento

    pagamento = PagamentoFiado.objects.select_related(
        "conta__cliente", "conta__company"
    ).get(pk=pagamento_fiado_id)

    tipo = Notificacao.TIPO_CONFIRMACAO_PAGAMENTO
    idem_key = f"confirmacao_pagamento:{pagamento_fiado_id}"

    if _verificar_duplicata(
        company_id=pagamento.conta.company_id,
        origem_tipo="PagamentoFiado",
        origem_id=pagamento.pk,
        tipo=tipo,
    ):
        return Notificacao.objects.filter(
            company_id=pagamento.conta.company_id,
            origem_tipo="PagamentoFiado",
            origem_id=pagamento.pk,
            tipo=tipo,
        ).latest("created_at")

    cliente = pagamento.conta.cliente
    telefone = getattr(cliente, "telefone", None) or ""
    if not telefone:
        raise NotificacaoError(
            "SEM_TELEFONE",
            f"Cliente {cliente.pk} não possui telefone cadastrado.",
        )

    mensagem = (
        f"Recebemos seu pagamento de R$ {pagamento.valor:.2f}. Obrigado, {cliente.nome}!"
    )

    payload = {
        "valor": str(pagamento.valor),
        "componentes": componentes_confirmacao_pagamento(
            cliente_nome=cliente.nome,
            valor=pagamento.valor,
        ),
    }

    notificacao = criar_notificacao(
        company_id=pagamento.conta.company_id,
        tipo=tipo,
        destinatario_nome=cliente.nome,
        destinatario_contato=telefone,
        mensagem=mensagem,
        payload=payload,
        origem_tipo="PagamentoFiado",
        origem_id=pagamento.pk,
        idempotency_key=idem_key,
        created_by=created_by,
    )

    return notificacao


def enviar_lembrete_vencimento(
    *,
    conta_fiado_id,
    created_by=None,
) -> Notificacao:
    from apps.fiado.models import ContaFiado
    from .templates import componentes_lembrete_vencimento

    conta = ContaFiado.objects.select_related("cliente", "company").get(pk=conta_fiado_id)
    cliente = conta.cliente
    telefone = getattr(cliente, "telefone", None) or ""
    if not telefone:
        raise NotificacaoError(
            "SEM_TELEFONE",
            f"Cliente {cliente.pk} não possui telefone cadastrado.",
        )

    if not conta.data_vencimento:
        raise NotificacaoError("SEM_VENCIMENTO", "Conta sem data de vencimento.")

    hoje = timezone.localdate()
    dias_restantes = (conta.data_vencimento - hoje).days
    data_venc = conta.data_vencimento.strftime("%d/%m/%Y")

    tipo = Notificacao.TIPO_LEMBRETE_VENCIMENTO
    idem_key = f"lembrete_vencimento:{conta_fiado_id}:{hoje}"

    mensagem = (
        f"Olá {cliente.nome}, sua conta vence em {data_venc} "
        f"(em {dias_restantes} dia(s)). Saldo: R$ {conta.valor_restante:.2f}."
    )

    payload = {
        "dias_restantes": dias_restantes,
        "data_vencimento": data_venc,
        "componentes": componentes_lembrete_vencimento(
            cliente_nome=cliente.nome,
            valor_restante=conta.valor_restante,
            data_vencimento=data_venc,
            dias_restantes=dias_restantes,
        ),
    }

    notificacao = criar_notificacao(
        company_id=conta.company_id,
        tipo=tipo,
        destinatario_nome=cliente.nome,
        destinatario_contato=telefone,
        mensagem=mensagem,
        payload=payload,
        origem_tipo="ContaFiado",
        origem_id=conta.pk,
        idempotency_key=idem_key,
        created_by=created_by,
    )

    return notificacao
