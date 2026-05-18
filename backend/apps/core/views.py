from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema


class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Health Check",
        description="Verifica se a API está no ar.",
        responses={200: {"type": "object", "properties": {"status": {"type": "string"}}}},
        tags=["Health"],
    )
    def get(self, request):
        return Response({"status": "ok"})
