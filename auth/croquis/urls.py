from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Configurar o router para a API
router = DefaultRouter()
router.register(r'croquis', views.CroquisViewSet)

urlpatterns = [
    # Views principais
    path('', views.croquis_list, name='croquis_list'),
    path('ajax/load-pontos/', views.ajax_load_pontos, name='ajax_load_pontos'),
    path('new/', views.CroquisCreateView.as_view(), name='croquis_create'),
    path('<int:pk>/', views.CroquisDetailView.as_view(), name='croquis_detail'),
    path('<int:pk>/edit/', views.CroquisUpdateView.as_view(), name='croquis_edit'),
    path('<int:pk>/delete/', views.CroquisDeleteView.as_view(), name='croquis_delete'),
    path('<int:pk>/review/', views.CroquisReviewView.as_view(), name='croquis_review'),
    
    # Batch upload
    path('batch-upload/<int:ponto_id>/', views.batch_upload_croquis, name='batch_upload_croquis'),
    
    # API URLs
    path('api/', include(router.urls)),
]
