from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.core.exceptions import require_company
from apps.core.models import AuditLog
from apps.core.services import create_audit_log

from ..models import BoletoOCR, HistoricoBoleto, OCRProcessamento
from .extracao import extrair_dados_boleto
from .ocr import get_ocr_provider
from .validators import validate_boleto_file


def _json_value(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _json_dict(data: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_value(value) for key, value in data.items()}


def boleto_snapshot(boleto: BoletoOCR) -> dict[str, Any]:
    return {
        "id": str(boleto.pk),
        "company_id": str(boleto.company_id),
        "arquivo_nome_original": boleto.arquivo_nome_original,
        "tipo_arquivo": boleto.tipo_arquivo,
        "content_type": boleto.content_type,
        "tamanho_bytes": boleto.tamanho_bytes,
        "sha256": boleto.sha256,
        "status": boleto.status,
        "fornecedor_id": str(boleto.fornecedor_id) if boleto.fornecedor_id else None,
        "fornecedor_nome": boleto.fornecedor_nome,
        "documento_beneficiario": boleto.documento_beneficiario,
        "documento_pagador": boleto.documento_pagador,
        "banco_codigo": boleto.banco_codigo,
        "banco_nome": boleto.banco_nome,
        "valor": str(boleto.valor) if boleto.valor is not None else None,
        "vencimento": boleto.vencimento.isoformat() if boleto.vencimento else None,
        "data_emissao": boleto.data_emissao.isoformat() if boleto.data_emissao else None,
        "linha_digitavel": boleto.linha_digitavel,
        "codigo_barras": boleto.codigo_barras,
        "confianca_ocr": str(boleto.confianca_ocr),
        "conta_pagar_id": str(boleto.conta_pagar_id) if boleto.conta_pagar_id else None,
        "created_by_id": str(boleto.created_by_id) if boleto.created_by_id else None,
        "processado_por_id": str(boleto.processado_por_id) if boleto.processado_por_id else None,
        "confirmado_por_id": str(boleto.confirmado_por_id) if boleto.confirmado_por_id else None,
        "rejeitado_por_id": str(boleto.rejeitado_por_id) if boleto.rejeitado_por_id else None,
        "tentativas_ocr": boleto.tentativas_ocr,
        "erro_codigo": boleto.erro_codigo,
        "erro_mensagem": boleto.erro_mensagem,
        "motivo_rejeicao": boleto.motivo_rejeicao,
        "observacao": boleto.observacao,
        "idempotency_key": boleto.idempotency_key,
    }


def _request_id(request) -> str:
    return getattr(request, "request_id", "") if request else ""


def criar_historico_boleto(
    *,
    boleto: BoletoOCR,
    evento: str,
    descricao: str,
    user=None,
    before=None,
    after=None,
    metadata=None,
    request=None,
) -> HistoricoBoleto:
    return HistoricoBoleto.objects.create(
        company=boleto.company,
        boleto=boleto,
        evento=evento,
        descricao=descricao,
        before=before,
        after=after,
        metadata=metadata or {},
        request_id=_request_id(request),
        created_by=user,
    )


def _full_clean_or_400(obj) -> None:
    try:
        obj.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(getattr(exc, "message_dict", exc.messages))


def _locked_boleto(*, boleto_id, company_id) -> BoletoOCR:
    try:
        return (
            BoletoOCR.objects.select_for_update(of=("self",))
            .select_related("company", "fornecedor", "conta_pagar", "created_by")
            .get(pk=boleto_id, company_id=company_id, deleted_at__isnull=True)
        )
    except (BoletoOCR.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        raise NotFound("Boleto não encontrado.")


def _save_boleto(boleto: BoletoOCR, *, update_fields: list[str]) -> None:
    _full_clean_or_400(boleto)
    boleto.save(update_fields=[*update_fields, "updated_at"])


def _save_processamento(processamento: OCRProcessamento, *, update_fields: list[str]) -> None:
    _full_clean_or_400(processamento)
    processamento._allow_update = True
    processamento.save(update_fields=[*update_fields, "updated_at"])
    processamento._allow_update = False


def _enqueue_ocr(boleto: BoletoOCR) -> None:
    from ..tasks import processar_boleto_ocr

    transaction.on_commit(lambda: processar_boleto_ocr.delay(str(boleto.pk)))


@transaction.atomic
def criar_boleto_upload(*, user, arquivo, observacao: str = "", idempotency_key: str = "", request=None) -> BoletoOCR:
    require_company(user)
    meta = validate_boleto_file(arquivo)
    key = (idempotency_key or "").strip()
    if key:
        existing = BoletoOCR.objects.filter(
            company_id=user.company_id,
            idempotency_key=key,
            deleted_at__isnull=True,
        ).first()
        if existing:
            return existing
    if BoletoOCR.objects.filter(company_id=user.company_id, sha256=meta["sha256"], deleted_at__isnull=True).exists():
        raise ValidationError({"arquivo": "Arquivo já enviado para esta empresa."})

    boleto = BoletoOCR(
        company=user.company,
        arquivo=arquivo,
        arquivo_nome_original=arquivo.name,
        tipo_arquivo=meta["tipo_arquivo"],
        content_type=meta["content_type"],
        tamanho_bytes=meta["tamanho_bytes"],
        sha256=meta["sha256"],
        preview_pages=meta["preview_pages"],
        observacao=observacao or "",
        idempotency_key=key,
        created_by=user,
    )
    _full_clean_or_400(boleto)
    try:
        boleto.save()
    except IntegrityError as exc:
        raise ValidationError({"arquivo": "Boleto duplicado para esta empresa."}) from exc

    after = boleto_snapshot(boleto)
    create_audit_log(user=user, action=AuditLog.ACTION_CREATE, entity=boleto, after=after, request=request)
    criar_historico_boleto(
        boleto=boleto,
        evento=HistoricoBoleto.EVENTO_UPLOAD_REALIZADO,
        descricao="Upload de boleto realizado.",
        user=user,
        after=after,
        request=request,
    )
    _enqueue_ocr(boleto)
    return boleto


def _company_id_for(boleto_id) -> str:
    try:
        return BoletoOCR.objects.only("company_id").get(pk=boleto_id).company_id
    except (BoletoOCR.DoesNotExist, ValueError, TypeError):
        raise NotFound("Boleto não encontrado.")


@transaction.atomic
def iniciar_processamento_ocr(*, boleto_id, task_id: str = "") -> tuple[BoletoOCR, OCRProcessamento]:
    provider = get_ocr_provider()
    boleto = _locked_boleto(
        boleto_id=boleto_id,
        company_id=_company_id_for(boleto_id),
    )
    if boleto.status in {BoletoOCR.STATUS_CONFIRMADO, BoletoOCR.STATUS_REJEITADO, BoletoOCR.STATUS_PROCESSANDO}:
        raise ValidationError({"status": "Boleto não pode ser processado no status atual."})

    before = boleto_snapshot(boleto)
    now = timezone.now()
    boleto.status = BoletoOCR.STATUS_PROCESSANDO
    boleto.ocr_started_at = now
    boleto.ocr_finished_at = None
    boleto.erro_codigo = ""
    boleto.erro_mensagem = ""
    boleto.tentativas_ocr += 1
    _save_boleto(
        boleto,
        update_fields=[
            "status",
            "ocr_started_at",
            "ocr_finished_at",
            "erro_codigo",
            "erro_mensagem",
            "tentativas_ocr",
        ],
    )
    processamento = OCRProcessamento.objects.create(
        company=boleto.company,
        boleto=boleto,
        provider=provider.name,
        tentativa=boleto.tentativas_ocr,
        task_id=task_id or "",
        started_at=now,
    )
    after = boleto_snapshot(boleto)
    create_audit_log(user=boleto.created_by, action=AuditLog.ACTION_UPDATE, entity=boleto, before=before, after=after)
    criar_historico_boleto(
        boleto=boleto,
        evento=HistoricoBoleto.EVENTO_OCR_INICIADO,
        descricao="Processamento OCR iniciado.",
        user=boleto.created_by,
        before=before,
        after=after,
        metadata={"provider": provider.name, "tentativa": boleto.tentativas_ocr},
    )
    return boleto, processamento


@transaction.atomic
def concluir_ocr_boleto(*, boleto_id, processamento_id, result, user=None) -> BoletoOCR:
    boleto = _locked_boleto(
        boleto_id=boleto_id,
        company_id=_company_id_for(boleto_id),
    )
    try:
        processamento = OCRProcessamento.objects.select_for_update(of=("self",)).get(
            pk=processamento_id,
            boleto=boleto,
            company=boleto.company,
        )
    except OCRProcessamento.DoesNotExist:
        raise NotFound("Processamento OCR não encontrado.")
    if boleto.status != BoletoOCR.STATUS_PROCESSANDO:
        return boleto

    before = boleto_snapshot(boleto)
    extracted = extrair_dados_boleto(result.text)
    campos = extracted.campos
    now = timezone.now()

    boleto.texto_ocr = result.text
    boleto.payload_ocr = result.payload
    boleto.raw_provider_response = result.raw_response
    boleto.campos_extraidos = _json_dict(campos)
    boleto.campos_confianca = extracted.confiancas
    boleto.confianca_ocr = extracted.confianca
    boleto.status = BoletoOCR.STATUS_AGUARDANDO_REVISAO
    boleto.processado_por = user
    boleto.ocr_finished_at = now
    boleto.fornecedor_nome = campos.get("fornecedor_nome") or ""
    boleto.documento_beneficiario = campos.get("documento_beneficiario") or ""
    boleto.documento_pagador = campos.get("documento_pagador") or ""
    boleto.banco_codigo = campos.get("banco_codigo") or ""
    boleto.banco_nome = campos.get("banco_nome") or ""
    boleto.valor = campos.get("valor")
    boleto.vencimento = campos.get("vencimento")
    boleto.linha_digitavel = campos.get("linha_digitavel") or ""
    boleto.codigo_barras = campos.get("codigo_barras") or ""
    _save_boleto(
        boleto,
        update_fields=[
            "texto_ocr",
            "payload_ocr",
            "raw_provider_response",
            "campos_extraidos",
            "campos_confianca",
            "confianca_ocr",
            "status",
            "processado_por",
            "ocr_finished_at",
            "fornecedor_nome",
            "documento_beneficiario",
            "documento_pagador",
            "banco_codigo",
            "banco_nome",
            "valor",
            "vencimento",
            "linha_digitavel",
            "codigo_barras",
        ],
    )

    processamento.status = OCRProcessamento.STATUS_SUCESSO
    processamento.finished_at = now
    processamento.duration_ms = int((now - (processamento.started_at or now)).total_seconds() * 1000)
    processamento.texto_extraido = result.text
    processamento.payload_response = result.payload
    processamento.raw_provider_response = result.raw_response
    processamento.confianca_ocr = extracted.confianca
    _save_processamento(
        processamento,
        update_fields=[
            "status",
            "finished_at",
            "duration_ms",
            "texto_extraido",
            "payload_response",
            "raw_provider_response",
            "confianca_ocr",
        ],
    )

    after = boleto_snapshot(boleto)
    create_audit_log(user=user or boleto.created_by, action=AuditLog.ACTION_UPDATE, entity=boleto, before=before, after=after)
    criar_historico_boleto(
        boleto=boleto,
        evento=HistoricoBoleto.EVENTO_OCR_CONCLUIDO,
        descricao="Processamento OCR concluído.",
        user=user or boleto.created_by,
        before=before,
        after=after,
        metadata={"processamento_id": str(processamento.pk), "confianca": str(extracted.confianca)},
    )
    return boleto


@transaction.atomic
def falhar_ocr_boleto(
    *,
    boleto_id,
    processamento_id,
    erro_codigo: str,
    erro_mensagem: str,
    timeout: bool = False,
    user=None,
) -> BoletoOCR:
    boleto = _locked_boleto(
        boleto_id=boleto_id,
        company_id=_company_id_for(boleto_id),
    )
    processamento = OCRProcessamento.objects.select_for_update(of=("self",)).get(
        pk=processamento_id,
        boleto=boleto,
        company=boleto.company,
    )
    before = boleto_snapshot(boleto)
    now = timezone.now()
    if boleto.status == BoletoOCR.STATUS_PROCESSANDO:
        boleto.status = BoletoOCR.STATUS_ERRO
        boleto.ocr_finished_at = now
        boleto.erro_codigo = erro_codigo
        boleto.erro_mensagem = erro_mensagem
        _save_boleto(
            boleto,
            update_fields=["status", "ocr_finished_at", "erro_codigo", "erro_mensagem"],
        )
    processamento.status = OCRProcessamento.STATUS_TIMEOUT if timeout else OCRProcessamento.STATUS_ERRO
    processamento.finished_at = now
    processamento.duration_ms = int((now - (processamento.started_at or now)).total_seconds() * 1000)
    processamento.erro_codigo = erro_codigo
    processamento.erro_mensagem = erro_mensagem
    _save_processamento(
        processamento,
        update_fields=["status", "finished_at", "duration_ms", "erro_codigo", "erro_mensagem"],
    )
    after = boleto_snapshot(boleto)
    create_audit_log(user=user or boleto.created_by, action=AuditLog.ACTION_UPDATE, entity=boleto, before=before, after=after)
    criar_historico_boleto(
        boleto=boleto,
        evento=HistoricoBoleto.EVENTO_OCR_FALHOU,
        descricao="Processamento OCR falhou.",
        user=user or boleto.created_by,
        before=before,
        after=after,
        metadata={"erro_codigo": erro_codigo, "processamento_id": str(processamento.pk)},
    )
    return boleto



@transaction.atomic
def reprocessar_boleto(*, user, boleto: BoletoOCR, request=None) -> BoletoOCR:
    require_company(user)
    boleto = _locked_boleto(boleto_id=boleto.pk, company_id=user.company_id)
    if boleto.status not in {BoletoOCR.STATUS_ERRO, BoletoOCR.STATUS_AGUARDANDO_REVISAO}:
        raise ValidationError({"status": "Somente boletos com erro ou aguardando revisão podem ser reprocessados."})
    before = boleto_snapshot(boleto)
    boleto.status = BoletoOCR.STATUS_ENVIADO
    boleto.erro_codigo = ""
    boleto.erro_mensagem = ""
    _save_boleto(boleto, update_fields=["status", "erro_codigo", "erro_mensagem"])
    after = boleto_snapshot(boleto)
    create_audit_log(user=user, action=AuditLog.ACTION_UPDATE, entity=boleto, before=before, after=after, request=request)
    criar_historico_boleto(
        boleto=boleto,
        evento=HistoricoBoleto.EVENTO_OCR_REPROCESSADO,
        descricao="Boleto enviado para reprocessamento OCR.",
        user=user,
        before=before,
        after=after,
        request=request,
    )
    _enqueue_ocr(boleto)
    return boleto


@transaction.atomic
def rejeitar_boleto(*, user, boleto: BoletoOCR, motivo: str, request=None) -> BoletoOCR:
    require_company(user)
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError({"motivo": "Motivo é obrigatório."})
    boleto = _locked_boleto(boleto_id=boleto.pk, company_id=user.company_id)
    if boleto.status in {BoletoOCR.STATUS_CONFIRMADO, BoletoOCR.STATUS_PROCESSANDO, BoletoOCR.STATUS_REJEITADO}:
        raise ValidationError({"status": "Boleto não pode ser rejeitado no status atual."})

    before = boleto_snapshot(boleto)
    boleto.status = BoletoOCR.STATUS_REJEITADO
    boleto.rejeitado_por = user
    boleto.rejeitado_at = timezone.now()
    boleto.motivo_rejeicao = motivo
    _save_boleto(boleto, update_fields=["status", "rejeitado_por", "rejeitado_at", "motivo_rejeicao"])
    after = boleto_snapshot(boleto)
    create_audit_log(user=user, action=AuditLog.ACTION_UPDATE, entity=boleto, before=before, after=after, request=request)
    criar_historico_boleto(
        boleto=boleto,
        evento=HistoricoBoleto.EVENTO_REJEITADO,
        descricao="Boleto rejeitado.",
        user=user,
        before=before,
        after=after,
        request=request,
    )
    return boleto
