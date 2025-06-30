from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .utils import api_check_auth

router = DefaultRouter()
router.register(r'clientes', views.ClienteViewSet)
router.register(r'codigos', views.CodigoViewSet)
router.register(r'pontos', views.PontoViewSet)

urlpatterns = [
    # Views principais
    path('', views.trabalho_list, name='trabalho_list'),
    
    # Cliente URLs
    path('cliente/create/', views.cliente_create, name='cliente_create'),
    path('cliente/<int:pk>/edit/', views.cliente_edit, name='cliente_edit'),
    path('cliente/<int:pk>/update/', views.cliente_update, name='cliente_update'),
    path('cliente/<int:pk>/delete/', views.cliente_delete, name='cliente_delete'),
    
    # Código URLs
    path('codigo/create/', views.codigo_create, name='codigo_create'),
    path('codigo/<int:pk>/edit/', views.codigo_edit, name='codigo_edit'),
    path('codigo/<int:pk>/update/', views.codigo_update, name='codigo_update'),
    path('codigo/<int:pk>/delete/', views.codigo_delete, name='codigo_delete'),
    
    # Ponto URLs
    path('ponto/create/', views.ponto_create, name='ponto_create'),
    path('ponto/<int:pk>/edit/', views.ponto_edit, name='ponto_edit'),
    path('ponto/<int:pk>/update/', views.ponto_update, name='ponto_update'),
    path('ponto/<int:pk>/delete/', views.ponto_delete, name='ponto_delete'),
    path('ponto/bulk-delete/', views.ponto_bulk_delete, name='ponto_bulk_delete'),
    path('ponto/<int:pk>/', views.ponto_detail, name='ponto_detail'),
    # Add images to existing detail
    path('ponto/<int:pk>/add-images/<int:detail_id>/', views.ponto_detail_add_images, name='ponto_detail_add_images'),
    # Delete detail item (movimento, observacao)
    path('ponto/<int:pk>/delete-detail/<int:detail_id>/', views.ponto_detail_delete, name='ponto_detail_delete'),
    # Delete image
    path('ponto/<int:pk>/delete-image/<int:image_id>/', views.ponto_detail_delete_image, name='ponto_detail_delete_image'),
    
    # API URLs
    path('api/pontos/bulk-create/', views.bulk_create_pontos, name='bulk-create-pontos'),
    path('api/', include(router.urls)),
    path('api/check-auth/', api_check_auth, name='api_check_auth'),


] 