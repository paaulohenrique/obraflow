from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.exceptions import require_company
from apps.core.models import AuditLog
from apps.core.services import create_audit_log
from apps.financeiro.models import CategoriaFinanceira
from apps.financeiro.services import criar_conta_pagar

from ..models import BoletoOCR, HistoricoBoleto
from .boleto import _locked_boleto, _save_boleto, boleto_snapshot, criar_historico_boleto


def _ensure_category_is_expense(categoria: CategoriaFinanceira, company_id) -> None:
    if categoria.company_id != company_id:
        raise ValidationError({"categoria": "Categoria não pertence à empresa."})
    if categoria.tipo != CategoriaFinanceira.TIPO_DESPESA:
        raise ValidationError({"categoria": "Conta a pagar exige categoria de despesa."})
    if not categoria.ativa or not categoria.is_active:
        raise ValidationError({"categoria": "Categoria financeira inativa."})


def _ensure_no_duplicate_identifiers(boleto: BoletoOCR, data: dict[str, Any]) -> None:
    checks = {
        "linha_digitavel": (data.get("linha_digitavel") or "").strip(),
        "codigo_barras": (data.get("codigo_barras") or "").strip(),
    }
    for field, value in checks.items():
        if not value:
            continue
        exists = BoletoOCR.objects.filter(
            company_id=boleto.company_id,
            deleted_at__isnull=True,
            **{field: value},
        ).exclude(pk=boleto.pk).exists()
        if exists:
            raise ValidationError({field: "Já existe boleto com este identificador para a empresa."})


def _descricao_boleto(data: dict[str, Any]) -> str:
    fornecedor = (data.get("beneficiario_nome") or "").strip()
    banco = (data.get("banco_nome") or data.get("banco_codigo") or "").strip()
    if fornecedor and banco:
        return f"Boleto - {fornecedor} ({banco})"[:255]
    if fornecedor:
        return f"Boleto - {fornecedor}"[:255]
    if banco:
        return f"Boleto - {banco}"[:255]
    return "Boleto OCR"


def _observacao_boleto(boleto: BoletoOCR, data: dict[str, Any]) -> str:
    parts = [
        f"BoletoOCR: {boleto.pk}",
        f"Linha digitável: {data.get('linha_digitavel') or '-'}",
        f"Código de barras: {data.get('codigo_barras') or '-'}",
    ]
    if data.get("observacao"):
        parts.append(str(data["observacao"]))
    return "\n".join(parts)


@transaction.atomic
def confirmar_boleto(*, user, boleto: BoletoOCR, data: dict[str, Any], request=None) -> BoletoOCR:
    require_company(user)
    boleto = _locked_boleto(boleto_id=boleto.pk, company_id=user.company_id)
    if boleto.status != BoletoOCR.STATUS_AGUARDANDO_REVISAO:
        raise ValidationError({"status": "Somente boleto aguardando revisão pode ser confirmado."})
    if boleto.conta_pagar_id:
        raise ValidationError({"conta_pagar": "Boleto já possui conta a pagar."})

    categoria = data["categoria"]
    fornecedor = data.get("fornecedor")
    _ensure_category_is_expense(categoria, user.company_id)
    if fornecedor and fornecedor.company_id != user.company_id:
        raise ValidationError({"fornecedor": "Fornecedor não pertence à empresa."})
    _ensure_no_duplicate_identifiers(boleto, data)

    before = boleto_snapshot(boleto)
    conta = criar_conta_pagar(
        user=user,
        data={
            "fornecedor": fornecedor,
            "categoria": categoria,
            "descricao": _descricao_boleto(data),
            "valor_total": data["valor"],
            "data_emissao": data.get("data_emissao") or boleto.data_emissao or timezone.localdate(),
            "data_vencimento": data["vencimento"],
            "observacao": _observacao_boleto(boleto, data),
        },
        request=request,
    )

    boleto.fornecedor = fornecedor
    boleto.fornecedor_nome = data.get("beneficiario_nome") or boleto.fornecedor_nome
    boleto.documento_beneficiario = data.get("beneficiario_documento") or boleto.documento_beneficiario
    boleto.banco_codigo = data.get("banco_codigo") or boleto.banco_codigo
    boleto.banco_nome = data.get("banco_nome") or boleto.banco_nome
    boleto.valor = data["valor"]
    boleto.vencimento = data["vencimento"]
    boleto.data_emissao = data.get("data_emissao") or boleto.data_emissao
    boleto.linha_digitavel = (data.get("linha_digitavel") or "").strip()
    boleto.codigo_barras = (data.get("codigo_barras") or "").strip()
    boleto.observacao = data.get("observacao") or boleto.observacao
    boleto.conta_pagar = conta
    boleto.status = BoletoOCR.STATUS_CONFIRMADO
    boleto.confirmado_por = user
    boleto.confirmado_at = timezone.now()
    _save_boleto(
        boleto,
        update_fields=[
            "fornecedor",
            "fornecedor_nome",
            "documento_beneficiario",
            "banco_codigo",
            "banco_nome",
            "valor",
            "vencimento",
            "data_emissao",
            "linha_digitavel",
            "codigo_barras",
            "observacao",
            "conta_pagar",
            "status",
            "confirmado_por",
            "confirmado_at",
        ],
    )

    after = boleto_snapshot(boleto)
    create_audit_log(user=user, action=AuditLog.ACTION_UPDATE, entity=boleto, before=before, after=after, request=request)
    criar_historico_boleto(
        boleto=boleto,
        evento=HistoricoBoleto.EVENTO_CONTA_PAGAR_CRIADA,
        descricao="Conta a pagar criada a partir do boleto.",
        user=user,
        metadata={"conta_pagar_id": str(conta.pk)},
        request=request,
    )
    criar_historico_boleto(
        boleto=boleto,
        evento=HistoricoBoleto.EVENTO_CONFIRMADO,
        descricao="Boleto confirmado manualmente.",
        user=user,
        before=before,
        after=after,
        request=request,
    )
    return boleto
