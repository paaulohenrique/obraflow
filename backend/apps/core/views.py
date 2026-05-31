import logging

from django.db import connection
from django.core.cache import cache
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema

logger = logging.getLogger("apps.core")

_HEALTH_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["status", "database", "redis"],
    "properties": {
        "status":   {"type": "string", "enum": ["ok", "error"]},
        "database": {"type": "string", "enum": ["ok", "error"]},
        "redis":    {"type": "string", "enum": ["ok", "error"]},
    },
}


def _check_database() -> str:
    try:
        connection.ensure_connection()
        return "ok"
    except Exception:
        logger.exception("HealthCheck: database connection failed")
        return "error"


def _check_redis() -> str:
    try:
        cache.set("_health", "1", timeout=5)
        if cache.get("_health") == "1":
            return "ok"
        return "error"
    except Exception:
        logger.exception("HealthCheck: redis connection failed")
        return "error"


class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Health Check",
        description=(
            "Verifica conectividade com banco de dados e Redis. "
            "Retorna HTTP 503 se qualquer serviço crítico estiver indisponível."
        ),
        responses={
            200: _HEALTH_RESPONSE_SCHEMA,
            503: _HEALTH_RESPONSE_SCHEMA,
        },
        tags=["Health"],
    )
    def get(self, request):
        db_status = _check_database()
        redis_status = _check_redis()

        overall = "ok" if db_status == "ok" and redis_status == "ok" else "error"
        http_status = status.HTTP_200_OK if overall == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE

        return Response(
            {
                "status": overall,
                "database": db_status,
                "redis": redis_status,
            },
            status=http_status,
        )
