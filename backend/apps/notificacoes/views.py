import logging

from django.conf import settings
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import NotificacaoFilter, TemplateNotificacaoFilter
from .models import CanalNotificacao, Notificacao, TemplateNotificacao
from .permissions import NotificacaoPermission, WebhookPermission
from .selectors import (
    canais_da_empresa,
    dashboard_notificacoes,
    notificacoes_da_empresa,
    templates_da_empresa,
)
from .serializers import (
    CanalNotificacaoSerializer,
    CanalNotificacaoWriteSerializer,
    DashboardSerializer,
    EnviarCobrancaFiadoSerializer,
    EnviarConfirmacaoPagamentoSerializer,
    NotificacaoSerializer,
    TemplateNotificacaoSerializer,
)

logger = logging.getLogger("apps.notificacoes")


@extend_schema_view(
    list=extend_schema(tags=["Notificações"]),
    retrieve=extend_schema(tags=["Notificações"]),
    reenviar=extend_schema(tags=["Notificações"]),
    dashboard=extend_schema(tags=["Notificações"]),
)
class NotificacaoViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [NotificacaoPermission]
    serializer_class = NotificacaoSerializer
    filterset_class = NotificacaoFilter
    search_fields = ["destinatario_nome", "destinatario_contato"]
    ordering_fields = ["created_at", "sent_at", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return notificacoes_da_empresa(self.request.user.company_id)

    @extend_schema(tags=["Notificações"], responses={200: NotificacaoSerializer})
    @action(detail=True, methods=["post"], url_path="reenviar")
    def reenviar(self, request: Request, pk=None):
        notificacao = self.get_object()
        if not notificacao.pode_reenviar:
            return Response(
                {"error": True, "detail": "Apenas notificações com status FALHOU podem ser reenviadas."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        notificacao.status = Notificacao.STATUS_PENDENTE
        notificacao.erro_codigo = ""
        notificacao.erro_mensagem = ""
        notificacao.failed_at = None
        notificacao.save(
            update_fields=["status", "erro_codigo", "erro_mensagem", "failed_at", "updated_at"]
        )
        from .tasks import enviar_notificacao_whatsapp
        enviar_notificacao_whatsapp.apply_async(
            args=[str(notificacao.pk)],
            queue="notificacoes",
        )
        return Response(NotificacaoSerializer(notificacao).data)

    @extend_schema(tags=["Notificações"], responses={200: DashboardSerializer})
    @action(detail=False, methods=["get"], url_path="dashboard")
    def dashboard(self, request: Request):
        data = dashboard_notificacoes(request.user.company_id)
        return Response(DashboardSerializer(data).data)


@extend_schema_view(
    list=extend_schema(tags=["Templates Notificação"]),
    retrieve=extend_schema(tags=["Templates Notificação"]),
    create=extend_schema(tags=["Templates Notificação"]),
    partial_update=extend_schema(tags=["Templates Notificação"]),
    update=extend_schema(tags=["Templates Notificação"]),
)
class TemplateNotificacaoViewSet(viewsets.ModelViewSet):
    permission_classes = [NotificacaoPermission]
    serializer_class = TemplateNotificacaoSerializer
    filterset_class = TemplateNotificacaoFilter
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return templates_da_empresa(self.request.user.company_id)


@extend_schema_view(
    list=extend_schema(tags=["Canais Notificação"]),
    retrieve=extend_schema(tags=["Canais Notificação"]),
    create=extend_schema(tags=["Canais Notificação"]),
    partial_update=extend_schema(tags=["Canais Notificação"]),
)
class CanalNotificacaoViewSet(viewsets.ModelViewSet):
    permission_classes = [NotificacaoPermission]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return canais_da_empresa(self.request.user.company_id)

    def get_serializer_class(self):
        if self.action in ("create", "partial_update", "update"):
            return CanalNotificacaoWriteSerializer
        return CanalNotificacaoSerializer

    def create(self, request, *args, **kwargs):
        from django.db import IntegrityError
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response(
                {"error": True, "detail": "Já existe um canal ativo deste tipo para a empresa."},
                status=status.HTTP_400_BAD_REQUEST,
            )


@extend_schema(tags=["WhatsApp"])
class EnviarCobrancaFiadoView(APIView):
    permission_classes = [NotificacaoPermission]
    action = "enviar_cobranca_fiado"

    def post(self, request: Request):
        serializer = EnviarCobrancaFiadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conta_fiado_id = serializer.validated_data["conta_fiado_id"]

        from django.core.exceptions import ObjectDoesNotExist

        from .services.whatsapp import NotificacaoError, enviar_cobranca_fiado

        try:
            notificacao = enviar_cobranca_fiado(
                conta_fiado_id=conta_fiado_id,
                created_by=request.user,
            )
        except NotificacaoError as exc:
            return Response(
                {"error": True, "detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ObjectDoesNotExist:
            return Response(
                {"error": True, "detail": "Conta fiado não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        from .tasks import enviar_notificacao_whatsapp
        enviar_notificacao_whatsapp.apply_async(
            args=[str(notificacao.pk)],
            queue="notificacoes",
        )
        return Response(NotificacaoSerializer(notificacao).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["WhatsApp"])
class EnviarConfirmacaoPagamentoView(APIView):
    permission_classes = [NotificacaoPermission]
    action = "enviar_confirmacao_pagamento"

    def post(self, request: Request):
        serializer = EnviarConfirmacaoPagamentoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pagamento_fiado_id = serializer.validated_data["pagamento_fiado_id"]

        from django.core.exceptions import ObjectDoesNotExist

        from .services.whatsapp import NotificacaoError, enviar_confirmacao_pagamento

        try:
            notificacao = enviar_confirmacao_pagamento(
                pagamento_fiado_id=pagamento_fiado_id,
                created_by=request.user,
            )
        except NotificacaoError as exc:
            return Response(
                {"error": True, "detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ObjectDoesNotExist:
            return Response(
                {"error": True, "detail": "Pagamento não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        from .tasks import enviar_notificacao_whatsapp
        enviar_notificacao_whatsapp.apply_async(
            args=[str(notificacao.pk)],
            queue="notificacoes",
        )
        return Response(NotificacaoSerializer(notificacao).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["WhatsApp Webhook"])
class WhatsAppWebhookView(APIView):
    permission_classes = [WebhookPermission]
    authentication_classes = []

    def get(self, request: Request):
        """Verificação de assinatura do webhook Meta."""
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")

        verify_token = getattr(settings, "WHATSAPP_WEBHOOK_VERIFY_TOKEN", "")
        if verify_token and mode == "subscribe" and token == verify_token:
            return Response(int(challenge) if challenge and challenge.isdigit() else challenge)
        return Response({"error": True, "detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    def post(self, request: Request):
        """Recebe eventos de status da Meta."""
        try:
            from .services.webhooks import processar_evento_webhook, verificar_assinatura_webhook

            sig = request.META.get("HTTP_X_HUB_SIGNATURE_256", "")
            if sig and not verificar_assinatura_webhook(request.body, sig):
                logger.warning("Assinatura webhook inválida recebida.")
                return Response(
                    {"error": True, "detail": "Assinatura inválida."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            processar_evento_webhook(request.data)
        except Exception:
            logger.exception("Erro inesperado ao processar webhook WhatsApp.")

        return Response({"status": "ok"})
