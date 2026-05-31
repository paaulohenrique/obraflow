from django.core.files.storage import default_storage
from django.http import FileResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view

from apps.core.pagination import StandardResultsSetPagination

from .filters import BoletoOCRFilter
from .models import BoletoOCR
from .permissions import BoletoPermission
from .selectors import get_boleto_by_id, get_dashboard_boletos, get_historico, search_boletos
from .serializers import (
    BoletoConfirmarSerializer,
    BoletoOCRDetailSerializer,
    BoletoOCRListSerializer,
    BoletoRejeitarSerializer,
    BoletoReprocessarSerializer,
    BoletoUploadSerializer,
    DashboardBoletosSerializer,
    HistoricoBoletoSerializer,
)
from .services.boleto import criar_boleto_upload, rejeitar_boleto, reprocessar_boleto
from .services.financeiro import confirmar_boleto


_ORDERING = {
    "created_at",
    "-created_at",
    "vencimento",
    "-vencimento",
    "valor",
    "-valor",
    "status",
    "-status",
    "confianca_ocr",
    "-confianca_ocr",
}


@extend_schema_view(
    list=extend_schema(summary="Listar boletos OCR", tags=["Boletos"]),
    retrieve=extend_schema(summary="Detalhar boleto OCR", tags=["Boletos"]),
)
class BoletoOCRViewSet(viewsets.GenericViewSet):
    queryset = BoletoOCR.objects.none()
    serializer_class = BoletoOCRDetailSerializer
    permission_classes = [BoletoPermission]
    filterset_class = BoletoOCRFilter
    search_fields = ["fornecedor_nome", "banco_nome", "linha_digitavel", "codigo_barras", "arquivo_nome_original"]
    ordering_fields = ["created_at", "vencimento", "valor", "status", "confianca_ocr"]
    ordering = ["-created_at"]

    def _serializer_context(self):
        return {"request": self.request}

    def _paginated(self, qs, serializer_class):
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, self.request, view=self)
        return paginator.get_paginated_response(serializer_class(page, many=True).data)

    def _ordering(self):
        ordering = self.request.query_params.get("ordering", "-created_at")
        return ordering if ordering in _ORDERING else "-created_at"

    def get_object(self):
        boleto = get_boleto_by_id(user=self.request.user, boleto_id=self.kwargs["pk"])
        self.check_object_permissions(self.request, boleto)
        return boleto

    def list(self, request):
        qs = search_boletos(user=request.user, filters=request.query_params.dict()).order_by(self._ordering())
        return self._paginated(qs, BoletoOCRListSerializer)

    def retrieve(self, request, pk=None):
        return Response(BoletoOCRDetailSerializer(self.get_object()).data)

    @extend_schema(
        summary="Upload de boleto para OCR",
        request=BoletoUploadSerializer,
        responses={201: BoletoOCRDetailSerializer},
        examples=[
            OpenApiExample(
                "Upload multipart",
                value={"arquivo": "<arquivo>", "observacao": "Conta de energia"},
                request_only=True,
            )
        ],
        tags=["Boletos"],
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="upload",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload(self, request):
        serializer = BoletoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        boleto = criar_boleto_upload(
            user=request.user,
            arquivo=serializer.validated_data["arquivo"],
            observacao=serializer.validated_data.get("observacao", ""),
            idempotency_key=serializer.validated_data.get("idempotency_key", ""),
            request=request,
        )
        return Response(BoletoOCRDetailSerializer(boleto).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Download do arquivo original do boleto",
        responses={(200, "application/octet-stream"): bytes},
        tags=["Boletos"],
    )
    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        boleto = self.get_object()
        if not boleto.arquivo:
            return Response({"detail": "Arquivo não encontrado."}, status=status.HTTP_404_NOT_FOUND)
        file_obj = default_storage.open(boleto.arquivo.name, "rb")
        return FileResponse(
            file_obj,
            as_attachment=True,
            filename=boleto.arquivo_nome_original,
            content_type=boleto.content_type or "application/octet-stream",
        )

    @extend_schema(
        summary="Histórico operacional do boleto",
        responses={200: HistoricoBoletoSerializer(many=True)},
        tags=["Boletos"],
    )
    @action(detail=True, methods=["get"], url_path="historico")
    def historico(self, request, pk=None):
        qs = get_historico(user=request.user, boleto_id=pk)
        return self._paginated(qs, HistoricoBoletoSerializer)

    @extend_schema(
        summary="Confirmar boleto e criar conta a pagar",
        request=BoletoConfirmarSerializer,
        responses={200: BoletoOCRDetailSerializer},
        tags=["Boletos"],
    )
    @action(detail=True, methods=["post"], url_path="confirmar")
    def confirmar(self, request, pk=None):
        boleto = self.get_object()
        serializer = BoletoConfirmarSerializer(data=request.data, context=self._serializer_context())
        serializer.is_valid(raise_exception=True)
        boleto = confirmar_boleto(
            user=request.user,
            boleto=boleto,
            data=serializer.validated_data,
            request=request,
        )
        return Response(BoletoOCRDetailSerializer(boleto).data)

    @extend_schema(
        summary="Rejeitar boleto OCR",
        request=BoletoRejeitarSerializer,
        responses={200: BoletoOCRDetailSerializer},
        tags=["Boletos"],
    )
    @action(detail=True, methods=["post"], url_path="rejeitar")
    def rejeitar(self, request, pk=None):
        boleto = self.get_object()
        serializer = BoletoRejeitarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        boleto = rejeitar_boleto(
            user=request.user,
            boleto=boleto,
            motivo=serializer.validated_data["motivo"],
            request=request,
        )
        return Response(BoletoOCRDetailSerializer(boleto).data)

    @extend_schema(
        summary="Reprocessar OCR do boleto",
        request=BoletoReprocessarSerializer,
        responses={200: BoletoOCRDetailSerializer},
        tags=["Boletos"],
    )
    @action(detail=True, methods=["post"], url_path="reprocessar")
    def reprocessar(self, request, pk=None):
        boleto = self.get_object()
        serializer = BoletoReprocessarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        boleto = reprocessar_boleto(user=request.user, boleto=boleto, request=request)
        return Response(BoletoOCRDetailSerializer(boleto).data)

    @extend_schema(
        summary="Dashboard de boletos OCR",
        responses={200: DashboardBoletosSerializer},
        tags=["Boletos"],
    )
    @action(detail=False, methods=["get"], url_path="dashboard")
    def dashboard(self, request):
        data = get_dashboard_boletos(user=request.user)
        return Response(DashboardBoletosSerializer(data).data)
