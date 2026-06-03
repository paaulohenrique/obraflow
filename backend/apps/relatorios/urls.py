from rest_framework.routers import DefaultRouter

from .views import (
    DashboardExecutivoViewSet,
    RelatorioEstoqueViewSet,
    RelatorioFiadoViewSet,
    RelatorioFinanceiroViewSet,
    RelatorioVendasViewSet,
)

router = DefaultRouter()
router.register("dashboard-executivo", DashboardExecutivoViewSet, basename="relatorio-dashboard")
router.register("fiado", RelatorioFiadoViewSet, basename="relatorio-fiado")
router.register("vendas", RelatorioVendasViewSet, basename="relatorio-vendas")
router.register("financeiro", RelatorioFinanceiroViewSet, basename="relatorio-financeiro")
router.register("estoque", RelatorioEstoqueViewSet, basename="relatorio-estoque")

urlpatterns = router.urls
