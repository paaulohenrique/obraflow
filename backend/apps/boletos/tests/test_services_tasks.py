from decimal import Decimal

import pytest
from django.test import override_settings
from rest_framework.exceptions import ValidationError

from apps.boletos.models import BoletoOCR, HistoricoBoleto, OCRProcessamento
from apps.boletos.services.boleto import (
    concluir_ocr_boleto,
    criar_boleto_upload,
    falhar_ocr_boleto,
    iniciar_processamento_ocr,
    rejeitar_boleto,
    reprocessar_boleto,
)
from apps.boletos.services.ocr import OCRResult
from apps.boletos.tasks import processar_boleto_ocr
from apps.core.models import AuditLog

from .conftest import fake_line, make_boleto, pdf_file


@pytest.mark.django_db
def test_criar_boleto_upload_persists_metadata_history_and_audit(admin_user):
    boleto = criar_boleto_upload(
        user=admin_user,
        arquivo=pdf_file("energia.pdf"),
        observacao="Conta de energia",
        idempotency_key="upload-1",
    )
    same = criar_boleto_upload(
        user=admin_user,
        arquivo=pdf_file("energia-outra.pdf", body=b"novo"),
        idempotency_key="upload-1",
    )

    assert boleto.pk == same.pk
    assert boleto.status == BoletoOCR.STATUS_ENVIADO
    assert boleto.tipo_arquivo == BoletoOCR.TIPO_PDF
    assert boleto.arquivo.name.startswith(f"boletos/{admin_user.company_id}/")
    assert HistoricoBoleto.objects.filter(boleto=boleto, evento=HistoricoBoleto.EVENTO_UPLOAD_REALIZADO).exists()
    assert AuditLog.objects.filter(entity_type="BoletoOCR", entity_id=boleto.pk).exists()


@pytest.mark.django_db
def test_criar_boleto_upload_rejects_duplicate_sha(admin_user):
    file_a = pdf_file("a.pdf", body=b"mesmo")
    file_b = pdf_file("b.pdf", body=b"mesmo")
    criar_boleto_upload(user=admin_user, arquivo=file_a)

    with pytest.raises(ValidationError):
        criar_boleto_upload(user=admin_user, arquivo=file_b)


@pytest.mark.django_db
def test_ocr_success_flow_extracts_fields_and_creates_processing(empresa_a, admin_user):
    boleto = make_boleto(empresa_a, admin_user, status=BoletoOCR.STATUS_ENVIADO)
    linha = fake_line()
    result = OCRResult(
        text=f"Beneficiário: Energisa\nCNPJ 45.997.418/0001-53\nLinha digitável {linha}\nValor R$ 123,45",
        payload={"ok": True},
        raw_response={"provider": "fake"},
    )

    boleto, processamento = iniciar_processamento_ocr(boleto_id=boleto.pk, task_id="task-1")
    assert boleto.status == BoletoOCR.STATUS_PROCESSANDO
    assert processamento.status == OCRProcessamento.STATUS_PROCESSANDO

    boleto = concluir_ocr_boleto(
        boleto_id=boleto.pk,
        processamento_id=processamento.pk,
        result=result,
        user=admin_user,
    )
    processamento.refresh_from_db()

    assert boleto.status == BoletoOCR.STATUS_AGUARDANDO_REVISAO
    assert boleto.linha_digitavel == linha
    assert boleto.valor == Decimal("123.45")
    assert boleto.confianca_ocr > 0
    assert processamento.status == OCRProcessamento.STATUS_SUCESSO
    assert HistoricoBoleto.objects.filter(boleto=boleto, evento=HistoricoBoleto.EVENTO_OCR_CONCLUIDO).exists()


@pytest.mark.django_db
def test_ocr_failure_and_reprocess_rules(empresa_a, admin_user):
    boleto = make_boleto(empresa_a, admin_user, status=BoletoOCR.STATUS_ENVIADO)
    boleto, processamento = iniciar_processamento_ocr(boleto_id=boleto.pk)

    boleto = falhar_ocr_boleto(
        boleto_id=boleto.pk,
        processamento_id=processamento.pk,
        erro_codigo="TIMEOUT",
        erro_mensagem="tempo excedido",
        timeout=True,
        user=admin_user,
    )
    processamento.refresh_from_db()
    assert boleto.status == BoletoOCR.STATUS_ERRO
    assert processamento.status == OCRProcessamento.STATUS_TIMEOUT

    boleto = reprocessar_boleto(user=admin_user, boleto=boleto)
    assert boleto.status == BoletoOCR.STATUS_ENVIADO
    assert HistoricoBoleto.objects.filter(boleto=boleto, evento=HistoricoBoleto.EVENTO_OCR_REPROCESSADO).exists()

    boleto.status = BoletoOCR.STATUS_CONFIRMADO
    boleto.conta_pagar = None
    BoletoOCR.objects.filter(pk=boleto.pk).update(status=BoletoOCR.STATUS_CONFIRMADO)
    with pytest.raises(ValidationError):
        reprocessar_boleto(user=admin_user, boleto=boleto)


@pytest.mark.django_db
def test_rejeitar_boleto_requires_reason_and_blocks_confirmed(empresa_a, admin_user):
    boleto = make_boleto(empresa_a, admin_user)
    with pytest.raises(ValidationError):
        rejeitar_boleto(user=admin_user, boleto=boleto, motivo="")

    boleto = rejeitar_boleto(user=admin_user, boleto=boleto, motivo="OCR ilegível")
    assert boleto.status == BoletoOCR.STATUS_REJEITADO
    assert boleto.motivo_rejeicao == "OCR ilegível"

    with pytest.raises(ValidationError):
        rejeitar_boleto(user=admin_user, boleto=boleto, motivo="novamente")


@pytest.mark.django_db
@override_settings(BOLETOS_FAKE_OCR_TEXT="Beneficiário: Energisa\nCNPJ 45.997.418/0001-53\nValor R$ 10,00\n30/06/2026")
def test_celery_task_processes_with_fake_provider(empresa_a, admin_user):
    boleto = make_boleto(empresa_a, admin_user, status=BoletoOCR.STATUS_ENVIADO)

    processar_boleto_ocr.apply(args=[str(boleto.pk)])
    boleto.refresh_from_db()

    assert boleto.status == BoletoOCR.STATUS_AGUARDANDO_REVISAO
    assert boleto.texto_ocr.startswith("Beneficiário")
    assert OCRProcessamento.objects.filter(boleto=boleto, status=OCRProcessamento.STATUS_SUCESSO).count() == 1
