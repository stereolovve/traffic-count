from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClienteViewSet, CodigoViewSet, PontoViewSet

router = DefaultRouter()
router.register(r'clientes', ClienteViewSet)
router.register(r'codigos', CodigoViewSet)
router.register(r'pontos', PontoViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
] 