from django.urls import include
from rest_framework.routers import DefaultRouter

from .views import VendaViewSet

router = DefaultRouter()
router.register("vendas", VendaViewSet, basename="vendas")

urlpatterns = router.urls
