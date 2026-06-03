from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CaixaDiarioViewSet,
    CategoriaFinanceiraViewSet,
    ConfiguracaoFinanceiraOperacionalViewSet,
    ContaFinanceiraViewSet,
    ContaPagarViewSet,
    DashboardFinanceiroViewSet,
    LancamentoFinanceiroViewSet,
)

router = DefaultRouter()
router.register("contas-financeiras", ContaFinanceiraViewSet, basename="financeiro-conta")
router.register(
    "configuracao-operacional",
    ConfiguracaoFinanceiraOperacionalViewSet,
    basename="financeiro-configuracao-operacional",
)
router.register("categorias", CategoriaFinanceiraViewSet, basename="financeiro-categoria")
router.register("lancamentos", LancamentoFinanceiroViewSet, basename="financeiro-lancamento")
router.register("contas-pagar", ContaPagarViewSet, basename="financeiro-conta-pagar")
router.register("caixas", CaixaDiarioViewSet, basename="financeiro-caixa")
router.register("dashboard", DashboardFinanceiroViewSet, basename="financeiro-dashboard")

urlpatterns = router.urls
