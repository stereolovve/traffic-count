# padroes/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import get_user_info, listar_preferences_usuario, atualizar_preferences_usuario

router = DefaultRouter()
router.register(r'padroes-api', views.PadraoContagemViewSet, basename='padroes-api')
router.register(r'user-padroes', views.UserPadraoContagemViewSet, basename='user-padroes')

urlpatterns = [
    path('', views.PadraoContagemListView.as_view(), name='padrao_list'),
    path('padroes/novo/', views.PadraoContagemCreateView.as_view(), name='padrao_create'),
    path('padroes/<int:pk>/editar/', views.PadraoContagemUpdateView.as_view(), name='padrao_edit'),
    path('padroes/<int:pk>/deletar/', views.PadraoContagemDeleteView.as_view(), name='padrao_delete'),
    path('tipos-de-padrao/', views.listar_tipos_padrao, name='listar_tipos_padrao'),
    path('padroes-globais/', views.listar_padroes_globais, name='listar_padroes_globais'),
    path('merged-binds/', views.get_user_or_global_padrao, name='merged-binds'),

    path('user/', views.get_user_info, name='user-redirect'),
    path('user/info/', get_user_info, name='get-user-info'),
    path('user/preferences/', listar_preferences_usuario, name='user-preferences'),
    path('user/preferences/update/', atualizar_preferences_usuario, name='update-user-preferences'),
]

urlpatterns += router.urls