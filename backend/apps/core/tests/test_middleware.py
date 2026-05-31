"""Tests for RequestLoggingMiddleware — Request ID injection and sanitization."""
import uuid
import pytest
from rest_framework.test import APIClient

from apps.core.middleware import _sanitize_request_id

HEALTH_URL = "/api/health/"


# ── Unit tests for _sanitize_request_id ──────────────────────────────────────

class TestSanitizeRequestId:
    def test_valid_uuid_passes_through(self):
        val = str(uuid.uuid4())
        assert _sanitize_request_id(val) == val

    def test_alphanumeric_and_hyphen_pass_through(self):
        assert _sanitize_request_id("abc-123-XYZ") == "abc-123-XYZ"

    def test_spaces_are_stripped(self):
        result = _sanitize_request_id("hello world")
        assert " " not in result
        assert result == "helloworld"

    def test_newline_is_stripped(self):
        result = _sanitize_request_id("abc\ndef")
        assert "\n" not in result
        assert result == "abcdef"

    def test_special_chars_are_stripped(self):
        result = _sanitize_request_id("req<script>alert(1)</script>id")
        assert "<" not in result
        assert ">" not in result

    def test_all_invalid_chars_returns_uuid(self):
        result = _sanitize_request_id("!!!@@@###")
        # All stripped → fallback to UUID
        parsed = uuid.UUID(result)
        assert parsed.version == 4

    def test_oversized_header_truncated_to_64(self):
        long_id = "a" * 200
        result = _sanitize_request_id(long_id)
        assert len(result) <= 64

    def test_exactly_64_valid_chars_kept_as_is(self):
        val = "a" * 64
        assert _sanitize_request_id(val) == val

    def test_65th_char_truncated(self):
        val = "a" * 65
        result = _sanitize_request_id(val)
        assert len(result) == 64

    def test_log_injection_via_newline_blocked(self):
        malicious = "legit-id\nERROR fake critical log line"
        result = _sanitize_request_id(malicious)
        assert "\n" not in result
        assert "ERROR" in result  # letters remain; only \n stripped
        assert len(result) <= 64


# ── Integration tests via HTTP ────────────────────────────────────────────────

@pytest.mark.django_db
class TestRequestID:
    def test_response_contains_x_request_id(self):
        client = APIClient()
        r = client.get(HEALTH_URL)
        assert "X-Request-ID" in r

    def test_generated_request_id_is_valid_uuid(self):
        client = APIClient()
        r = client.get(HEALTH_URL)
        request_id = r["X-Request-ID"]
        parsed = uuid.UUID(request_id)
        assert parsed.version == 4

    def test_valid_custom_request_id_is_preserved(self):
        client = APIClient()
        custom_id = str(uuid.uuid4())
        r = client.get(HEALTH_URL, HTTP_X_REQUEST_ID=custom_id)
        assert r["X-Request-ID"] == custom_id

    def test_each_request_gets_unique_id(self):
        client = APIClient()
        r1 = client.get(HEALTH_URL)
        r2 = client.get(HEALTH_URL)
        assert r1["X-Request-ID"] != r2["X-Request-ID"]

    def test_malicious_header_is_sanitized(self):
        client = APIClient()
        r = client.get(HEALTH_URL, HTTP_X_REQUEST_ID="bad\ninjection")
        assert "\n" not in r["X-Request-ID"]

    def test_oversized_header_is_truncated(self):
        client = APIClient()
        r = client.get(HEALTH_URL, HTTP_X_REQUEST_ID="a" * 200)
        assert len(r["X-Request-ID"]) <= 64

    def test_all_invalid_header_generates_uuid(self):
        client = APIClient()
        r = client.get(HEALTH_URL, HTTP_X_REQUEST_ID="!!!@@@###")
        request_id = r["X-Request-ID"]
        # All chars stripped → fallback UUID
        parsed = uuid.UUID(request_id)
        assert parsed.version == 4

    def test_error_response_contains_request_id(self, auth_client):
        """On a 404, the error envelope includes request_id."""
        r = auth_client.get("/api/v1/clientes/00000000-0000-0000-0000-000000000000/")
        assert r.status_code == 404
        assert "request_id" in r.data
