from decimal import Decimal

import pytest

from apps.boletos.models import BoletoOCR, HistoricoBoleto
from apps.core.models import AuditLog
from apps.financeiro.models import ContaPagar

from .conftest import fake_line, jpg_file, make_boleto, pdf_file


BOLETOS_URL = "/api/v1/boletos/"


def detail(pk):
    return f"{BOLETOS_URL}{pk}/"


def confirm_payload(despesa, fornecedor=None, **kwargs):
    payload = {
        "beneficiario_nome": "Energisa Teste",
        "beneficiario_documento": "45997418000153",
        "banco_codigo": "001",
        "banco_nome": "Banco do Brasil",
        "valor": "123.45",
        "vencimento": "2026-06-30",
        "linha_digitavel": fake_line(),
        "categoria": str(despesa.pk),
        "observacao": "Revisado no QA",
    }
    if fornecedor:
        payload["fornecedor"] = str(fornecedor.pk)
    payload.update(kwargs)
    return payload


@pytest.mark.django_db
class TestUploadAndRead:
    def test_upload_pdf_and_image(self, seller_client):
        r_pdf = seller_client.post(
            BOLETOS_URL + "upload/",
            data={"arquivo": pdf_file("boleto.pdf"), "observacao": "PDF"},
            format="multipart",
        )
        r_img = seller_client.post(
            BOLETOS_URL + "upload/",
            data={"arquivo": jpg_file("boleto.jpg"), "observacao": "Imagem"},
            format="multipart",
        )

        assert r_pdf.status_code == 201
        assert r_pdf.data["status"] == BoletoOCR.STATUS_ENVIADO
        assert r_pdf.data["tipo_arquivo"] == BoletoOCR.TIPO_PDF
        assert r_img.status_code == 201
        assert r_img.data["tipo_arquivo"] == BoletoOCR.TIPO_JPG

    def test_upload_validation_and_permissions(self, viewer_client, anon_client, seller_client):
        assert viewer_client.post(BOLETOS_URL + "upload/", data={}, format="multipart").status_code == 403
        assert anon_client.post(BOLETOS_URL + "upload/", data={}, format="multipart").status_code == 401

        r_missing = seller_client.post(BOLETOS_URL + "upload/", data={}, format="multipart")
        r_bad = seller_client.post(
            BOLETOS_URL + "upload/",
            data={"arquivo": pdf_file("fake.jpg")},
            format="multipart",
        )

        assert r_missing.status_code == 400
        assert r_bad.status_code == 400

    def test_list_filter_search_order_dashboard_and_seller_scope(
        self,
        admin_client,
        seller_client,
        admin_user,
        seller_user,
        empresa_a,
    ):
        boleto_admin = make_boleto(empresa_a, admin_user, fornecedor_nome="Fornecedor Admin")
        boleto_seller = make_boleto(
            empresa_a,
            seller_user,
            fornecedor_nome="Fornecedor Seller",
            status=BoletoOCR.STATUS_ERRO,
        )

        r_admin = admin_client.get(BOLETOS_URL + "?search=Fornecedor&ordering=status")
        r_seller = seller_client.get(BOLETOS_URL)
        r_filter = admin_client.get(BOLETOS_URL + "?status=ERRO")
        r_dash = admin_client.get(BOLETOS_URL + "dashboard/")

        assert r_admin.status_code == 200
        assert r_admin.data["count"] == 2
        assert r_seller.status_code == 200
        assert [item["id"] for item in r_seller.data["results"]] == [str(boleto_seller.pk)]
        assert r_filter.data["count"] == 1
        assert r_filter.data["results"][0]["id"] == str(boleto_seller.pk)
        assert r_dash.status_code == 200
        assert "pendentes_revisao" in r_dash.data
        assert BoletoOCR.objects.filter(pk=boleto_admin.pk).exists()

    def test_retrieve_download_history_and_tenant_isolation(
        self,
        admin_client,
        other_company_client,
        admin_user,
        empresa_a,
    ):
        boleto = make_boleto(empresa_a, admin_user)
        HistoricoBoleto.objects.create(
            company=empresa_a,
            boleto=boleto,
            evento=HistoricoBoleto.EVENTO_UPLOAD_REALIZADO,
            descricao="Upload",
            created_by=admin_user,
        )

        r_detail = admin_client.get(detail(boleto.pk))
        r_download = admin_client.get(f"{detail(boleto.pk)}download/")
        r_history = admin_client.get(f"{detail(boleto.pk)}historico/")

        assert r_detail.status_code == 200
        assert r_download.status_code == 200
        assert b"".join(r_download.streaming_content).startswith(b"%PDF")
        assert r_history.status_code == 200
        assert r_history.data["count"] == 1
        assert other_company_client.get(detail(boleto.pk)).status_code == 404
        assert other_company_client.get(f"{detail(boleto.pk)}download/").status_code == 404


@pytest.mark.django_db
class TestConfirmacaoFinanceiro:
    def test_manager_confirms_boleto_and_creates_conta_pagar(
        self,
        manager_client,
        manager_user,
        empresa_a,
        despesa,
        fornecedor,
    ):
        boleto = make_boleto(empresa_a, manager_user)

        r = manager_client.post(
            f"{detail(boleto.pk)}confirmar/",
            data=confirm_payload(despesa, fornecedor),
            format="json",
        )
        boleto.refresh_from_db()
        conta = ContaPagar.objects.get(pk=boleto.conta_pagar_id)

        assert r.status_code == 200
        assert boleto.status == BoletoOCR.STATUS_CONFIRMADO
        assert boleto.confirmado_por == manager_user
        assert conta.status == ContaPagar.STATUS_ABERTA
        assert conta.valor_total == Decimal("123.45")
        assert conta.valor_restante == Decimal("123.45")
        assert conta.fornecedor == fornecedor
        assert "BoletoOCR" in conta.observacao
        assert HistoricoBoleto.objects.filter(boleto=boleto, evento=HistoricoBoleto.EVENTO_CONFIRMADO).exists()
        assert AuditLog.objects.filter(entity_type="ContaPagar", entity_id=conta.pk).exists()

        r_again = manager_client.post(
            f"{detail(boleto.pk)}confirmar/",
            data=confirm_payload(despesa, fornecedor),
            format="json",
        )
        assert r_again.status_code == 400
        assert ContaPagar.objects.filter(boleto_ocr=boleto).count() == 1

    def test_confirm_validation_errors(
        self,
        manager_client,
        manager_user,
        empresa_a,
        despesa,
        receita,
    ):
        boleto = make_boleto(empresa_a, manager_user)

        r_bad_value = manager_client.post(
            f"{detail(boleto.pk)}confirmar/",
            data=confirm_payload(despesa, valor="0.00"),
            format="json",
        )
        r_bad_category = manager_client.post(
            f"{detail(boleto.pk)}confirmar/",
            data=confirm_payload(receita),
            format="json",
        )
        r_bad_line = manager_client.post(
            f"{detail(boleto.pk)}confirmar/",
            data=confirm_payload(despesa, linha_digitavel="123"),
            format="json",
        )

        assert r_bad_value.status_code == 400
        assert r_bad_category.status_code == 400
        assert r_bad_line.status_code == 400

    def test_rejected_and_duplicate_boleto_do_not_confirm(
        self,
        manager_client,
        manager_user,
        empresa_a,
        despesa,
    ):
        existing = make_boleto(empresa_a, manager_user, linha_digitavel=fake_line())
        boleto = make_boleto(empresa_a, manager_user)

        r_duplicate = manager_client.post(
            f"{detail(boleto.pk)}confirmar/",
            data=confirm_payload(despesa),
            format="json",
        )
        assert r_duplicate.status_code == 400

        existing.status = BoletoOCR.STATUS_REJEITADO
        existing.motivo_rejeicao = "duplicado"
        existing.save(update_fields=["status", "motivo_rejeicao", "updated_at"])
        r_rejected = manager_client.post(
            f"{detail(existing.pk)}confirmar/",
            data=confirm_payload(despesa, linha_digitavel=""),
            format="json",
        )
        assert r_rejected.status_code == 400

    def test_permissions_for_confirm_reject_reprocess(
        self,
        seller_client,
        viewer_client,
        manager_client,
        seller_user,
        empresa_a,
        despesa,
    ):
        boleto = make_boleto(empresa_a, seller_user)
        assert viewer_client.post(f"{detail(boleto.pk)}confirmar/", data=confirm_payload(despesa), format="json").status_code == 403
        assert seller_client.post(f"{detail(boleto.pk)}confirmar/", data=confirm_payload(despesa), format="json").status_code == 403

        r_reject = manager_client.post(f"{detail(boleto.pk)}rejeitar/", data={"motivo": "ilegível"}, format="json")
        assert r_reject.status_code == 200
        assert r_reject.data["status"] == BoletoOCR.STATUS_REJEITADO

        assert manager_client.post(f"{detail(boleto.pk)}reprocessar/", data={}, format="json").status_code == 400

        boleto.status = BoletoOCR.STATUS_ERRO
        boleto.motivo_rejeicao = ""
        boleto.save(update_fields=["status", "motivo_rejeicao", "updated_at"])
        assert manager_client.post(f"{detail(boleto.pk)}reprocessar/", data={}, format="json").status_code == 200
