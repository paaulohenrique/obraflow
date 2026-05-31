from rest_framework.routers import SimpleRouter

from .views import (
    ContaFiadoViewSet,
    DashboardFiadoViewSet,
    ItemFiadoViewSet,
    PagamentoFiadoViewSet,
)

router = SimpleRouter()
router.register("contas", ContaFiadoViewSet, basename="fiado-conta")
router.register("itens", ItemFiadoViewSet, basename="fiado-item")
router.register("pagamentos", PagamentoFiadoViewSet, basename="fiado-pagamento")
router.register("dashboard", DashboardFiadoViewSet, basename="fiado-dashboard")

urlpatterns = router.urls
