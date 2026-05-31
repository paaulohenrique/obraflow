import logging

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("apps.core")


def require_company(user) -> None:
    """Raise PermissionDenied if the user has no associated company.

    Call this at the top of any permission class or service that operates on
    tenant-scoped data. Superusers bypassing tenant scope must be handled
    explicitly before calling this helper.
    """
    if not getattr(user, "company_id", None):
        raise PermissionDenied("Usuário sem empresa associada.")


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
    request = context.get("request")
    request_id = getattr(request, "request_id", None)

    if response is not None:
        body = {
            "error": True,
            "status_code": response.status_code,
            "detail": _extract_detail(response.data),
        }
        if request_id:
            body["request_id"] = request_id
        response.data = body
        return response

    logger.exception(
        "Unhandled exception at %s request_id=%s",
        request.path if request else "unknown",
        request_id,
        exc_info=exc,
    )
    body = {"error": True, "status_code": 500, "detail": "Erro interno do servidor."}
    if request_id:
        body["request_id"] = request_id
    return Response(body, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
