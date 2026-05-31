"""Tests for the custom_exception_handler envelope format."""
import pytest
from django.urls import path
from rest_framework import serializers, status
from rest_framework.exceptions import (
    AuthenticationFailed,
    MethodNotAllowed,
    NotFound,
    ParseError,
    PermissionDenied,
    Throttled,
    UnsupportedMediaType,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.views import APIView

from apps.core.exceptions import _extract_detail, custom_exception_handler


# ── Unit tests for _extract_detail ───────────────────────────────────────────

class TestExtractDetail:
    def test_flattens_single_detail_key(self):
        assert _extract_detail({"detail": "Not found."}) == "Not found."

    def test_keeps_field_errors(self):
        data = {"email": ["Este campo é obrigatório."]}
        assert _extract_detail(data) == data

    def test_keeps_list_errors(self):
        data = ["Erro 1", "Erro 2"]
        assert _extract_detail(data) == data

    def test_keeps_multi_key_dict(self):
        data = {"detail": "x", "extra": "y"}
        assert _extract_detail(data) == data

    def test_converts_error_detail_to_str(self):
        from rest_framework.exceptions import ErrorDetail
        ed = ErrorDetail("Not found.", code="not_found")
        result = _extract_detail({"detail": ed})
        assert result == "Not found."
        assert isinstance(result, str)


# ── Integration-style tests using the handler directly ───────────────────────

def _make_response(exc):
    """Call the handler and return the envelope data dict."""
    from rest_framework.views import exception_handler as drf_handler
    context = {"request": None, "view": None, "args": (), "kwargs": {}}
    resp = custom_exception_handler(exc, context)
    return resp


class TestCustomExceptionHandlerEnvelope:
    def test_not_found_flat_detail(self):
        resp = _make_response(NotFound("Cliente não encontrado."))
        assert resp.status_code == 404
        assert resp.data["error"] is True
        assert resp.data["status_code"] == 404
        assert resp.data["detail"] == "Cliente não encontrado."
        assert not isinstance(resp.data["detail"], dict)

    def test_permission_denied_flat(self):
        resp = _make_response(PermissionDenied())
        assert resp.status_code == 403
        assert isinstance(resp.data["detail"], str)

    def test_authentication_failed_flat(self):
        resp = _make_response(AuthenticationFailed())
        assert resp.status_code == 401
        assert isinstance(resp.data["detail"], str)

    def test_parse_error_flat(self):
        resp = _make_response(ParseError("JSON inválido."))
        assert resp.status_code == 400
        assert resp.data["detail"] == "JSON inválido."

    def test_method_not_allowed_flat(self):
        resp = _make_response(MethodNotAllowed("DELETE"))
        assert resp.status_code == 405
        assert isinstance(resp.data["detail"], str)

    def test_unsupported_media_type_flat(self):
        resp = _make_response(UnsupportedMediaType("text/xml"))
        assert resp.status_code == 415
        assert isinstance(resp.data["detail"], str)

    def test_throttled_flat(self):
        resp = _make_response(Throttled(wait=10))
        assert resp.status_code == 429
        assert isinstance(resp.data["detail"], str)

    def test_validation_error_field_dict_preserved(self):
        exc = ValidationError({"cpf_cnpj": "CPF inválido."})
        resp = _make_response(exc)
        assert resp.status_code == 400
        assert isinstance(resp.data["detail"], dict)
        assert "cpf_cnpj" in resp.data["detail"]

    def test_validation_error_non_field(self):
        exc = ValidationError("Dados inválidos.")
        resp = _make_response(exc)
        assert resp.status_code == 400
        assert resp.data["error"] is True

    def test_envelope_always_has_required_keys(self):
        # When called without a real request (request=None), request_id is absent.
        for exc in [NotFound(), PermissionDenied(), ValidationError("x")]:
            resp = _make_response(exc)
            assert {"error", "status_code", "detail"}.issubset(set(resp.data.keys()))

    def test_no_double_nesting(self):
        resp = _make_response(NotFound("Test"))
        detail = resp.data["detail"]
        # Must NOT be {"detail": "Test"}
        assert not (isinstance(detail, dict) and "detail" in detail)
