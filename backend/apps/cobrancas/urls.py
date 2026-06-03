from django.urls import path

from .views import CobrancaViewSet, ConfiguracaoCobrancaViewSet

cobrancas_list = CobrancaViewSet.as_view({"get": "list"})
cobrancas_dashboard = CobrancaViewSet.as_view({"get": "dashboard"})
cobrancas_preview = CobrancaViewSet.as_view({"post": "preview"})
cobrancas_enviar = CobrancaViewSet.as_view({"post": "enviar"})
cobrancas_enviar_lote = CobrancaViewSet.as_view({"post": "enviar_lote"})
cobrancas_historico_cliente = CobrancaViewSet.as_view({"get": "historico_cliente"})
cobrancas_recuperacao = CobrancaViewSet.as_view({"get": "recuperacao"})
cobrancas_templates = CobrancaViewSet.as_view({"post": "templates_operacionais"})
cobrancas_configuracao = ConfiguracaoCobrancaViewSet.as_view({
    "get": "list",
    "patch": "partial_update",
})

urlpatterns = [
    path("", cobrancas_list, name="cobrancas-list"),
    path("dashboard/", cobrancas_dashboard, name="cobrancas-dashboard"),
    path("preview/", cobrancas_preview, name="cobrancas-preview"),
    path("enviar/", cobrancas_enviar, name="cobrancas-enviar"),
    path("lote/enviar/", cobrancas_enviar_lote, name="cobrancas-enviar-lote"),
    path("historico-cliente/", cobrancas_historico_cliente, name="cobrancas-historico-cliente"),
    path("recuperacao/", cobrancas_recuperacao, name="cobrancas-recuperacao"),
    path("templates-operacionais/", cobrancas_templates, name="cobrancas-templates-operacionais"),
    path("configuracao/", cobrancas_configuracao, name="cobrancas-configuracao"),
]
