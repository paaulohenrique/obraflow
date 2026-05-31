import logging
import re
import time
import uuid

logger = logging.getLogger("apps.core")

_MAX_REQUEST_ID_LEN = 64
# Allow only URL-safe printable chars; blocks newlines, spaces, and injection vectors.
_REQUEST_ID_SAFE = re.compile(r"[^a-zA-Z0-9\-]")


def _sanitize_request_id(raw: str) -> str:
    """Truncate to 64 chars and strip any character outside [a-zA-Z0-9\\-].

    Returns a fresh UUID if the cleaned value is empty (e.g. all characters
    were stripped from a malicious payload).
    """
    cleaned = _REQUEST_ID_SAFE.sub("", raw[:_MAX_REQUEST_ID_LEN])
    return cleaned or str(uuid.uuid4())


class RequestLoggingMiddleware:
    """Log every request with method, path, status, duration and request_id.

    Reads X-Request-ID from the incoming headers (useful when a load balancer
    or API gateway injects a correlation ID). Generates a fresh UUID when the
    header is absent. The ID is:
      - sanitized to [a-zA-Z0-9\\-], max 64 chars (prevents log injection)
      - stored on ``request.request_id`` for use in views / services
      - echoed back in the response header ``X-Request-ID``
      - included in every log line produced by this middleware
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        raw_id = request.META.get("HTTP_X_REQUEST_ID", "")
        request_id = _sanitize_request_id(raw_id) if raw_id else str(uuid.uuid4())
        request.request_id = request_id

        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        response["X-Request-ID"] = request_id

        logger.info(
            "%(method)s %(path)s %(status)s %(duration)sms request_id=%(rid)s",
            {
                "method": request.method,
                "path": request.get_full_path(),
                "status": response.status_code,
                "duration": duration_ms,
                "rid": request_id,
            },
        )
        return response
