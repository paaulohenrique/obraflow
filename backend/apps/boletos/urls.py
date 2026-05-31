from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import BoletoOCRViewSet

router = DefaultRouter()
router.register("", BoletoOCRViewSet, basename="boleto")

urlpatterns = router.urls
