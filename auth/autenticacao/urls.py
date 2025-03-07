# auth/autenticacao/urls.py
from django.urls import path
from .views import LoginView, RegisterView, PadraoContagemListView
from .views import PadraoContagemCreateView, PadraoContagemUpdateView, PadraoContagemDeleteView
from .views import UserPadraoContagemViewSet, get_user_or_global_padrao, get_user_info
from .views import listar_tipos_padrao, listar_padroes_globais, listar_preferences_usuario, atualizar_preferences_usuario, listar_binds_usuario
from .views import UserPreferencesView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework.routers import DefaultRouter
from .views import PadraoContagemViewSet

# 🔹 Criando as rotas de ViewSet automaticamente
router = DefaultRouter()
router.register(r'padroes-api', PadraoContagemViewSet, basename='padroes')
router.register(r'user-padroes', UserPadraoContagemViewSet, basename='user-padroes')

urlpatterns = [
    # 🔹 Autenticação
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),

    # Login e Refresh Token
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # 🔹 Padrões Globais
    path('padroes/', PadraoContagemListView.as_view(), name='padrao_list'),
    path('padroes/novo/', PadraoContagemCreateView.as_view(), name='padrao_create'),
    path('padroes/<int:pk>/editar/', PadraoContagemUpdateView.as_view(), name='padrao_edit'),
    path('padroes/<int:pk>/deletar/', PadraoContagemDeleteView.as_view(), name='padrao_delete'),
    path('tipos-de-padrao/', listar_tipos_padrao, name='listar_tipos_padrao'),
    path('padroes-globais/', listar_padroes_globais, name='listar_padroes_globais'),

    # 🔹 Preferences do Usuário
    path("user/", get_user_info, name="get-user-info"),
    path("user/binds/", listar_binds_usuario, name="listar_binds_usuario"),
    path("user/preferences/", listar_preferences_usuario, name="user-preferences"),
    path("user/preferences/update/", atualizar_preferences_usuario, name="update-user-preferences"),

    # 🔹 Merge entre Padrões Globais e Preferences do Usuário
    path('merged-binds/', get_user_or_global_padrao, name='merged-binds'),
]

# 🔹 Adicionando as rotas dos ViewSets registrados no router
urlpatterns += router.urls
