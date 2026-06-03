from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from apps.core.models import AuditLog
from apps.core.services import create_audit_log
from apps.fiado.models import ContaFiado, ZERO_MONEY
from apps.notificacoes.models import Notificacao, TemplateNotificacao
from apps.notificacoes.services.templates import componentes_cobranca_operacional
from apps.notificacoes.services.whatsapp import (
    NotificacaoError,
    _canal_whatsapp_ativo,
    _template_ativo,
    criar_notificacao,
)

from .selectors import contas_cobranca, get_configuracao_cobranca


@dataclass(frozen=True)
class ResultadoLoteCobranca:
    criterio: int
    quantidade: int
    valor_total: Decimal
    notificacoes: list[Notificacao]
    falhas: list[dict[str, str]]


TEMPLATE_VARIAVEIS_COBRANCA = [
    "nome",
    "valor",
    "data_vencimento",
    "dias_atraso",
    "empresa",
]

TEMPLATES_OPERACIONAIS = {
    Notificacao.TIPO_LEMBRETE_VENCIMENTO: {
        "nome": "Lembrete de vencimento",
        "corpo": (
            "Olá {{nome}}.\n\n"
            "Lembramos que existe um saldo de R$ {{valor}} com vencimento em "
            "{{data_vencimento}}.\n\n"
            "Entre em contato com a {{empresa}} para regularização.\n\n"
            "Obrigado."
        ),
        "variaveis": TEMPLATE_VARIAVEIS_COBRANCA,
    },
    Notificacao.TIPO_COBRANCA_1_DIA: {
        "nome": "Cobrança 1 dia em atraso",
        "corpo": (
            "Olá {{nome}}.\n\n"
            "Identificamos um saldo pendente de R$ {{valor}} com vencimento em "
            "{{data_vencimento}}.\n\n"
            "Entre em contato com a {{empresa}} para regularização.\n\n"
            "Obrigado."
        ),
        "variaveis": TEMPLATE_VARIAVEIS_COBRANCA,
    },
    Notificacao.TIPO_COBRANCA_7_DIAS: {
        "nome": "Cobrança 7 dias em atraso",
        "corpo": (
            "Olá {{nome}}.\n\n"
            "Sua conta possui saldo pendente de R$ {{valor}} há {{dias_atraso}} "
            "dias, com vencimento em {{data_vencimento}}.\n\n"
            "Entre em contato com a {{empresa}} para regularização.\n\n"
            "Obrigado."
        ),
        "variaveis": TEMPLATE_VARIAVEIS_COBRANCA,
    },
    Notificacao.TIPO_COBRANCA_15_DIAS: {
        "nome": "Cobrança 15 dias em atraso",
        "corpo": (
            "Olá {{nome}}.\n\n"
            "Consta um saldo pendente de R$ {{valor}} vencido em "
            "{{data_vencimento}}. Já são {{dias_atraso}} dias em atraso.\n\n"
            "Entre em contato com a {{empresa}} para regularização.\n\n"
            "Obrigado."
        ),
        "variaveis": TEMPLATE_VARIAVEIS_COBRANCA,
    },
    Notificacao.TIPO_COBRANCA_30_DIAS: {
        "nome": "Cobrança 30 dias em atraso",
        "corpo": (
            "Olá {{nome}}.\n\n"
            "Sua conta segue com saldo pendente de R$ {{valor}} desde "
            "{{data_vencimento}}, totalizando {{dias_atraso}} dias em atraso.\n\n"
            "Entre em contato com a {{empresa}} para regularização.\n\n"
            "Obrigado."
        ),
        "variaveis": TEMPLATE_VARIAVEIS_COBRANCA,
    },
    Notificacao.TIPO_AGRADECIMENTO_PAGAMENTO: {
        "nome": "Agradecimento de pagamento",
        "corpo": (
            "Olá {{nome}}.\n\n"
            "Recebemos seu pagamento de R$ {{valor}}. Obrigado por regularizar "
            "sua conta com a {{empresa}}."
        ),
        "variaveis": ["nome", "valor", "empresa"],
    },
}


TIPO_POR_CRITERIO = {
    -1: Notificacao.TIPO_LEMBRETE_VENCIMENTO,
    0: Notificacao.TIPO_LEMBRETE_VENCIMENTO,
    1: Notificacao.TIPO_COBRANCA_1_DIA,
    7: Notificacao.TIPO_COBRANCA_7_DIAS,
    15: Notificacao.TIPO_COBRANCA_15_DIAS,
    30: Notificacao.TIPO_COBRANCA_30_DIAS,
}


def garantir_templates_operacionais(*, company, user=None) -> list[TemplateNotificacao]:
    canal = _canal_whatsapp_ativo(company.pk)
    criados: list[TemplateNotificacao] = []
    for tipo, dados in TEMPLATES_OPERACIONAIS.items():
        existente = _template_ativo(company.pk, tipo, canal)
        if existente:
            continue
        template = TemplateNotificacao.objects.create(
            company=company,
            canal=canal,
            nome=dados["nome"],
            tipo=tipo,
            provider_template_name="",
            linguagem="pt_BR",
            categoria=TemplateNotificacao.CATEGORIA_UTILITY,
            corpo=dados["corpo"],
            variaveis=dados["variaveis"],
            ativo=True,
        )
        criados.append(template)
        create_audit_log(
            user=user,
            action=AuditLog.ACTION_CREATE,
            entity=template,
            after={"tipo": tipo, "nome": template.nome},
        )
    return criados


def montar_preview_cobranca(*, conta: ContaFiado, tipo: str | None = None) -> dict[str, Any]:
    conta = _conta_com_relacoes(conta)
    tipo_notificacao = tipo or tipo_cobranca_para_conta(conta)
    template = _template_ativo(conta.company_id, tipo_notificacao, _canal_whatsapp_ativo(conta.company_id))
    contexto = contexto_cobranca(conta)
    mensagem = _render_template(template.corpo if template else "", contexto)
    if not mensagem:
        mensagem = _render_template(
            TEMPLATES_OPERACIONAIS[Notificacao.TIPO_COBRANCA_1_DIA]["corpo"],
            contexto,
        )

    return {
        "conta_id": conta.pk,
        "cliente_id": conta.cliente_id,
        "cliente_nome": conta.cliente.nome,
        "valor": conta.valor_restante,
        "data_vencimento": conta.data_vencimento,
        "data_vencimento_formatada": contexto["data_vencimento"],
        "dias_atraso": conta.dias_atraso,
        "tipo": tipo_notificacao,
        "mensagem": mensagem,
    }


@transaction.atomic
def enviar_cobranca_conta(
    *,
    conta: ContaFiado,
    user=None,
    tipo: str | None = None,
    idempotency_key: str = "",
    request=None,
) -> Notificacao:
    conta = _conta_com_relacoes(conta)
    if user and conta.company_id != user.company_id:
        raise NotificacaoError("CONTA_NAO_ENCONTRADA", "Conta fiado não encontrada.")
    if conta.status != ContaFiado.STATUS_ABERTA or conta.valor_restante <= ZERO_MONEY:
        raise NotificacaoError(
            "CONTA_NAO_COBRAVEL",
            "Apenas contas abertas com saldo em aberto podem ser cobradas.",
        )

    cliente = conta.cliente
    telefone = (cliente.whatsapp or cliente.telefone or "").strip()
    if not telefone:
        raise NotificacaoError(
            "SEM_TELEFONE",
            f"Cliente {cliente.pk} não possui WhatsApp ou telefone cadastrado.",
        )

    garantir_templates_operacionais(company=conta.company, user=user)
    preview = montar_preview_cobranca(conta=conta, tipo=tipo)
    tipo_notificacao = preview["tipo"]
    data_venc = preview["data_vencimento_formatada"]
    componentes = componentes_cobranca_operacional(
        cliente_nome=cliente.nome,
        valor_restante=conta.valor_restante,
        data_vencimento=data_venc,
        dias_atraso=conta.dias_atraso,
    )

    if not idempotency_key:
        idempotency_key = (
            f"cobranca:{tipo_notificacao}:{conta.pk}:{timezone.localdate().isoformat()}"
        )

    payload = {
        "conta_id": str(conta.pk),
        "cliente_id": str(cliente.pk),
        "valor_restante": str(conta.valor_restante),
        "data_vencimento": data_venc,
        "dias_atraso": conta.dias_atraso,
        "componentes": componentes,
    }

    notificacao = criar_notificacao(
        company_id=conta.company_id,
        tipo=tipo_notificacao,
        destinatario_nome=cliente.nome,
        destinatario_contato=telefone,
        mensagem=preview["mensagem"],
        payload=payload,
        origem_tipo="ContaFiado",
        origem_id=conta.pk,
        idempotency_key=idempotency_key,
        created_by=user,
    )
    if notificacao.payload != payload or notificacao.mensagem != preview["mensagem"]:
        notificacao.payload = payload
        notificacao.mensagem = preview["mensagem"]
        notificacao.save(update_fields=["payload", "mensagem", "updated_at"])

    from apps.notificacoes.tasks import enviar_notificacao_whatsapp

    enviar_notificacao_whatsapp.apply_async(
        args=[str(notificacao.pk)],
        queue="notificacoes",
    )

    create_audit_log(
        user=user,
        action=AuditLog.ACTION_CREATE,
        entity=notificacao,
        after={
            "tipo": tipo_notificacao,
            "conta_id": str(conta.pk),
            "cliente_id": str(cliente.pk),
            "valor_restante": str(conta.valor_restante),
        },
        request=request,
    )
    return notificacao


def enviar_cobranca_lote(
    *,
    user,
    criterio: int,
    conta_ids: list[str] | None = None,
    idempotency_key: str = "",
    request=None,
) -> ResultadoLoteCobranca:
    if criterio not in {1, 7, 15, 30}:
        raise NotificacaoError(
            "CRITERIO_INVALIDO",
            "Critério de lote deve ser 1, 7, 15 ou 30 dias em atraso.",
        )

    qs = contas_cobranca(user.company_id, {"criterio": criterio})
    if conta_ids:
        qs = qs.filter(pk__in=conta_ids)

    tipo = TIPO_POR_CRITERIO[criterio]
    notificacoes: list[Notificacao] = []
    falhas: list[dict[str, str]] = []
    valor_total = Decimal("0.00")

    for conta in qs:
        valor_total += conta.valor_restante
        try:
            sub_key = (
                f"{idempotency_key}:{conta.pk}"
                if idempotency_key
                else f"cobranca-lote:{criterio}:{conta.pk}:{timezone.localdate().isoformat()}"
            )
            notificacao = enviar_cobranca_conta(
                conta=conta,
                user=user,
                tipo=tipo,
                idempotency_key=sub_key,
                request=request,
            )
            notificacoes.append(notificacao)
        except NotificacaoError as exc:
            falhas.append({"conta_id": str(conta.pk), "detail": exc.message, "code": exc.code})
        except ObjectDoesNotExist:
            falhas.append({"conta_id": str(conta.pk), "detail": "Conta fiado não encontrada.", "code": "NAO_ENCONTRADA"})

    return ResultadoLoteCobranca(
        criterio=criterio,
        quantidade=len(notificacoes),
        valor_total=valor_total,
        notificacoes=notificacoes,
        falhas=falhas,
    )


def executar_automacoes_cobranca(*, company, user=None) -> ResultadoLoteCobranca:
    config = get_configuracao_cobranca(company=company, user=user)
    if not config.ativo:
        return ResultadoLoteCobranca(criterio=0, quantidade=0, valor_total=Decimal("0.00"), notificacoes=[], falhas=[])

    criterios: list[int] = []
    if config.enviar_1_dia_antes:
        criterios.append(-1)
    if config.enviar_no_vencimento:
        criterios.append(0)
    if config.enviar_7_dias_apos:
        criterios.append(7)
    if config.enviar_15_dias_apos:
        criterios.append(15)
    if config.enviar_30_dias_apos:
        criterios.append(30)

    notificacoes: list[Notificacao] = []
    falhas: list[dict[str, str]] = []
    valor_total = Decimal("0.00")
    hoje = timezone.localdate()
    for criterio in criterios:
        alvo = hoje - timedelta(days=criterio)
        qs = contas_cobranca(company.pk).filter(data_vencimento=alvo)
        tipo = TIPO_POR_CRITERIO[criterio]
        for conta in qs:
            valor_total += conta.valor_restante
            try:
                notificacao = enviar_cobranca_conta(
                    conta=conta,
                    user=user,
                    tipo=tipo,
                    idempotency_key=f"cobranca-auto:{tipo}:{conta.pk}:{hoje.isoformat()}",
                )
                notificacoes.append(notificacao)
            except NotificacaoError as exc:
                falhas.append({"conta_id": str(conta.pk), "detail": exc.message, "code": exc.code})

    return ResultadoLoteCobranca(
        criterio=0,
        quantidade=len(notificacoes),
        valor_total=valor_total,
        notificacoes=notificacoes,
        falhas=falhas,
    )


def tipo_cobranca_para_conta(conta: ContaFiado) -> str:
    return TIPO_POR_CRITERIO.get(conta.dias_atraso, Notificacao.TIPO_COBRANCA_FIADO)


def contexto_cobranca(conta: ContaFiado) -> dict[str, str]:
    empresa = conta.company.nome_fantasia or conta.company.razao_social
    data_vencimento = (
        conta.data_vencimento.strftime("%d/%m/%Y") if conta.data_vencimento else "sem vencimento"
    )
    return {
        "nome": conta.cliente.nome,
        "valor": f"{conta.valor_restante:.2f}",
        "data_vencimento": data_vencimento,
        "dias_atraso": str(conta.dias_atraso),
        "empresa": empresa,
    }


def _conta_com_relacoes(conta: ContaFiado) -> ContaFiado:
    if hasattr(conta, "cliente") and hasattr(conta, "company"):
        return conta
    return ContaFiado.objects.select_related("cliente", "company").get(pk=conta.pk)


def _render_template(corpo: str, contexto: dict[str, Any]) -> str:
    corpo = (corpo or "").strip()
    if not corpo:
        return ""

    def repl(match):
        chave = match.group(1).strip()
        return str(contexto.get(chave, ""))

    return re.sub(r"{{\s*([\w_]+)\s*}}", repl, corpo)
