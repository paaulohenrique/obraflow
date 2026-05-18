import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("apps.core")


def _extract_detail(data):
    """Flatten DRF's single-key {\"detail\": msg} responses to just msg.

    DRF wraps NotFound / PermissionDenied / AuthenticationFailed / ParseError /
    MethodNotAllowed / UnsupportedMediaType / Throttled as {"detail": ErrorDetail}.
    ValidationError with field errors comes as {"field": [...]} — left as-is.
    """
    if isinstance(data, dict) and len(data) == 1 and "detail" in data:
        return str(data["detail"])
    return data


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            "error": True,
            "status_code": response.status_code,
            "detail": _extract_detail(response.data),
        }
        return response

    logger.exception(
        "Unhandled exception at %s",
        context.get("request", {}) and context["request"].path,
        exc_info=exc,
    )
    return Response(
        {"error": True, "status_code": 500, "detail": "Erro interno do servidor."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
