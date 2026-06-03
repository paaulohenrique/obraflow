from django.core.exceptions import ObjectDoesNotExist
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.fiado.models import ContaFiado
from apps.notificacoes.serializers import NotificacaoSerializer
from apps.notificacoes.services.whatsapp import NotificacaoError

from .models import ConfiguracaoCobranca
from .permissions import CobrancaPermission
from .selectors import (
    dashboard_cobrancas,
    get_configuracao_cobranca,
    historico_cobrancas_cliente,
    contas_cobranca,
    recuperacao_inadimplencia,
)
from .serializers import (
    CobrancaContaSerializer,
    CobrancaPreviewRequestSerializer,
    CobrancaPreviewSerializer,
    ConfiguracaoCobrancaSerializer,
    DashboardCobrancaSerializer,
    EnviarCobrancaSerializer,
    EnviarLoteCobrancaSerializer,
    ResultadoLoteCobrancaSerializer,
    TemplatesOperacionaisSerializer,
)
from .services import (
    enviar_cobranca_conta,
    enviar_cobranca_lote,
    garantir_templates_operacionais,
    montar_preview_cobranca,
)


@extend_schema_view(
    list=extend_schema(tags=["Cobranças"]),
    dashboard=extend_schema(tags=["Cobranças"]),
    preview=extend_schema(tags=["Cobranças"]),
    enviar=extend_schema(tags=["Cobranças"]),
    enviar_lote=extend_schema(tags=["Cobranças"]),
    historico_cliente=extend_schema(tags=["Cobranças"]),
    recuperacao=extend_schema(tags=["Cobranças"]),
    templates_operacionais=extend_schema(tags=["Cobranças"]),
)
class CobrancaViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [CobrancaPermission]
    serializer_class = CobrancaContaSerializer
    ordering = ["data_vencimento", "cliente__nome"]

    def get_queryset(self):
        return contas_cobranca(self.request.user.company_id, self.request.query_params)

    @extend_schema(responses={200: DashboardCobrancaSerializer})
    @action(detail=False, methods=["get"], url_path="dashboard")
    def dashboard(self, request: Request):
        data = dashboard_cobrancas(request.user.company_id, request.query_params)
        return Response(DashboardCobrancaSerializer(data).data)

    @extend_schema(
        request=CobrancaPreviewRequestSerializer,
        responses={200: CobrancaPreviewSerializer},
    )
    @action(detail=False, methods=["post"], url_path="preview")
    def preview(self, request: Request):
        serializer = CobrancaPreviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            conta = self._get_conta(serializer.validated_data["conta_id"])
            garantir_templates_operacionais(company=request.user.company, user=request.user)
            preview = montar_preview_cobranca(
                conta=conta,
                tipo=serializer.validated_data.get("tipo"),
            )
        except NotificacaoError as exc:
            return _erro(exc.message)
        except ObjectDoesNotExist:
            return _erro("Conta fiado não encontrada.", status.HTTP_404_NOT_FOUND)
        return Response(CobrancaPreviewSerializer(preview).data)

    @extend_schema(request=EnviarCobrancaSerializer, responses={201: NotificacaoSerializer})
    @action(detail=False, methods=["post"], url_path="enviar")
    def enviar(self, request: Request):
        serializer = EnviarCobrancaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            conta = self._get_conta(serializer.validated_data["conta_id"])
            notificacao = enviar_cobranca_conta(
                conta=conta,
                user=request.user,
                tipo=serializer.validated_data.get("tipo"),
                idempotency_key=serializer.validated_data.get("idempotency_key", ""),
                request=request,
            )
        except NotificacaoError as exc:
            return _erro(exc.message)
        except ObjectDoesNotExist:
            return _erro("Conta fiado não encontrada.", status.HTTP_404_NOT_FOUND)
        return Response(NotificacaoSerializer(notificacao).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=EnviarLoteCobrancaSerializer,
        responses={201: ResultadoLoteCobrancaSerializer},
    )
    @action(detail=False, methods=["post"], url_path="lote/enviar")
    def enviar_lote(self, request: Request):
        serializer = EnviarLoteCobrancaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            resultado = enviar_cobranca_lote(
                user=request.user,
                criterio=serializer.validated_data["criterio"],
                conta_ids=[str(pk) for pk in serializer.validated_data.get("conta_ids", [])],
                idempotency_key=serializer.validated_data.get("idempotency_key", ""),
                request=request,
            )
        except NotificacaoError as exc:
            return _erro(exc.message)

        data = {
            "criterio": resultado.criterio,
            "quantidade": resultado.quantidade,
            "valor_total": resultado.valor_total,
            "notificacoes": [n.pk for n in resultado.notificacoes],
            "falhas": resultado.falhas,
        }
        return Response(ResultadoLoteCobrancaSerializer(data).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses={200: NotificacaoSerializer(many=True)})
    @action(detail=False, methods=["get"], url_path="historico-cliente")
    def historico_cliente(self, request: Request):
        cliente_id = request.query_params.get("cliente")
        if not cliente_id:
            return _erro("Informe o cliente para consultar o histórico.")
        qs = historico_cobrancas_cliente(request.user.company_id, cliente_id)
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(NotificacaoSerializer(page, many=True).data)
        return Response(NotificacaoSerializer(qs, many=True).data)

    @extend_schema(responses={200: DashboardCobrancaSerializer})
    @action(detail=False, methods=["get"], url_path="recuperacao")
    def recuperacao(self, request: Request):
        data = recuperacao_inadimplencia(request.user.company_id, request.query_params)
        return Response(data)

    @extend_schema(responses={201: TemplatesOperacionaisSerializer})
    @action(detail=False, methods=["post"], url_path="templates-operacionais")
    def templates_operacionais(self, request: Request):
        try:
            templates = garantir_templates_operacionais(
                company=request.user.company,
                user=request.user,
            )
        except NotificacaoError as exc:
            return _erro(exc.message)
        data = {"criados": len(templates), "templates": [t.pk for t in templates]}
        return Response(TemplatesOperacionaisSerializer(data).data, status=status.HTTP_201_CREATED)

    def _get_conta(self, conta_id):
        return ContaFiado.objects.select_related("cliente", "company").get(
            pk=conta_id,
            company_id=self.request.user.company_id,
            deleted_at__isnull=True,
        )


@extend_schema_view(
    list=extend_schema(tags=["Configurações de Cobrança"]),
    partial_update=extend_schema(tags=["Configurações de Cobrança"]),
)
class ConfiguracaoCobrancaViewSet(viewsets.GenericViewSet):
    permission_classes = [CobrancaPermission]
    serializer_class = ConfiguracaoCobrancaSerializer

    def get_queryset(self):
        return ConfiguracaoCobranca.objects.filter(
            company_id=self.request.user.company_id,
            deleted_at__isnull=True,
        )

    def list(self, request: Request):
        configuracao = get_configuracao_cobranca(
            company=request.user.company,
            user=request.user,
        )
        return Response(ConfiguracaoCobrancaSerializer(configuracao).data)

    def partial_update(self, request: Request, pk=None):
        configuracao = get_configuracao_cobranca(
            company=request.user.company,
            user=request.user,
        )
        serializer = ConfiguracaoCobrancaSerializer(
            configuracao,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)


def _erro(detail: str, http_status=status.HTTP_400_BAD_REQUEST) -> Response:
    return Response({"error": True, "detail": detail}, status=http_status)
