from rest_framework.routers import SimpleRouter
from .views import EmpresaViewSet

router = SimpleRouter()
router.register("", EmpresaViewSet, basename="empresa")
urlpatterns = router.urls
