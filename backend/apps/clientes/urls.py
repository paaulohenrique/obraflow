from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import ClienteViewSet

router = SimpleRouter()
router.register("", ClienteViewSet, basename="cliente")

urlpatterns = router.urls
