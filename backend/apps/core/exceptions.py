import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger("apps.core")


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            "error": True,
            "status_code": response.status_code,
            "detail": response.data,
        }
        return response

    logger.exception("Unhandled exception", exc_info=exc, extra={"context": str(context)})
    return Response(
        {"error": True, "status_code": 500, "detail": "Erro interno do servidor."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
