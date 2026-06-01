from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CanalNotificacaoViewSet,
    EnviarCobrancaFiadoView,
    EnviarConfirmacaoPagamentoView,
    NotificacaoViewSet,
    TemplateNotificacaoViewSet,
    WhatsAppWebhookView,
)

router = DefaultRouter()
router.register("notificacoes", NotificacaoViewSet, basename="notificacao")
router.register("templates", TemplateNotificacaoViewSet, basename="template-notificacao")
router.register("canais", CanalNotificacaoViewSet, basename="canal-notificacao")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "whatsapp/enviar-cobranca-fiado/",
        EnviarCobrancaFiadoView.as_view(),
        name="whatsapp-cobranca-fiado",
    ),
    path(
        "whatsapp/enviar-confirmacao-pagamento/",
        EnviarConfirmacaoPagamentoView.as_view(),
        name="whatsapp-confirmacao-pagamento",
    ),
    path(
        "whatsapp/webhook/",
        WhatsAppWebhookView.as_view(),
        name="whatsapp-webhook",
    ),
]
