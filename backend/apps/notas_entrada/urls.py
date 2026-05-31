from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import NotaFiscalEntradaViewSet

router = DefaultRouter()
router.register("", NotaFiscalEntradaViewSet, basename="nota-entrada")

urlpatterns = router.urls
