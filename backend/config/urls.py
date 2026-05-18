from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from apps.core.views import HealthCheckView

api_v1 = [
    # Auth
    path("auth/", include("apps.accounts.urls")),
    # Platform
    path("empresas/", include("apps.empresas.urls")),
    # Business domains
    path("clientes/", include("apps.clientes.urls")),
    path("fiado/", include("apps.fiado.urls")),
    path("financeiro/", include("apps.financeiro.urls")),
    path("estoque/", include("apps.estoque.urls")),
    path("fiscal/", include("apps.fiscal.urls")),
    path("cobrancas/", include("apps.cobrancas.urls")),
    path("boletos/", include("apps.boletos.urls")),
    path("notificacoes/", include("apps.notificacoes.urls")),
    path("relatorios/", include("apps.relatorios.urls")),
    # API Docs
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthCheckView.as_view(), name="health-check"),
    path("api/v1/", include(api_v1)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    import debug_toolbar
    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
