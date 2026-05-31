import pytest
from rest_framework.exceptions import NotFound

from apps.boletos.filters import BoletoOCRFilter
from apps.boletos.selectors import get_boleto_by_id
from apps.boletos.services.ocr import FakeOCRProvider, GoogleVisionOCRProvider, OCRError
from apps.boletos.services.storage import preview_upload_path

from .conftest import make_boleto


def test_ocr_error_and_fake_provider_binary_branch(tmp_path, settings):
    settings.BOLETOS_FAKE_OCR_TEXT = ""
    path = tmp_path / "binary.jpg"
    path.write_bytes(b"\xff\xd8\xff\xe0")

    result = FakeOCRProvider().extract_text_from_file(str(path))
    error = OCRError("CODE", "Mensagem")

    assert result.text == ""
    assert result.confidence == 0.0
    assert error.code == "CODE"
    assert error.message == "Mensagem"


def test_google_provider_reports_missing_optional_dependency(tmp_path):
    path = tmp_path / "boleto.jpg"
    path.write_bytes(b"\xff\xd8\xff\xe0")

    with pytest.raises(OCRError) as exc:
        GoogleVisionOCRProvider().extract_text_from_file(str(path))

    assert exc.value.code == "GOOGLE_VISION_UNAVAILABLE"


def test_preview_upload_path_uses_company_and_filename(empresa_a):
    class Obj:
        pk = "boleto-id"
        company_id = empresa_a.pk

    path = preview_upload_path(Obj(), "Página 1.JPG")

    assert str(empresa_a.pk) in path
    assert path.endswith(".jpg")


@pytest.mark.django_db
def test_filter_search_empty_returns_queryset_and_selector_malformed_404(empresa_a, admin_user):
    boleto = make_boleto(empresa_a, admin_user, fornecedor_nome="Filtro")
    qs_empty = BoletoOCRFilter().filter_search(type(boleto).objects.all(), "search", "")
    qs_match = BoletoOCRFilter().filter_search(type(boleto).objects.all(), "search", "Filtro")
    qs_no_match = BoletoOCRFilter().filter_search(type(boleto).objects.all(), "search", "NaoExiste")

    assert boleto in list(qs_empty)
    assert boleto in list(qs_match)
    assert boleto not in list(qs_no_match)
    with pytest.raises(NotFound):
        get_boleto_by_id(user=admin_user, boleto_id="uuid-invalido")
