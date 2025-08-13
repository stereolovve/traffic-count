# folha_ponto/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Router para ViewSets
router = DefaultRouter()
router.register(r'work-codes', views.WorkCodeViewSet, basename='work-codes')
router.register(r'time-records', views.TimeRecordViewSet, basename='time-records')
router.register(r'salaries', views.SalaryViewSet, basename='salaries')

urlpatterns = [
    # =================== AUTENTICAÇÃO ===================
    # Endpoints compatíveis com o sistema original
    path('accounts/login/', views.folha_ponto_login, name='folha_ponto_login'),
    path('accounts/register/', views.folha_ponto_register, name='folha_ponto_register'),
    path('accounts/profile/', views.get_user_profile, name='get_user_profile'),
    path('accounts/profile/update/', views.update_user_profile, name='update_user_profile'),
    path('accounts/users/', views.get_all_users, name='get_all_users'),
    
    # Refresh token (reutiliza o do sistema principal)
    path('accounts/token/refresh/', include('autenticacao.urls')),
    
    # =================== DASHBOARD ===================
    path('timetrack/dashboard/', views.dashboard, name='dashboard'),
    
    # =================== RELATÓRIOS ===================
    path('timetrack/relatorio/<int:ano>/<int:mes>/', views.relatorio_mensal, name='relatorio_mensal'),
    path('timetrack/salario/calcular/', views.calcular_salario_mensal, name='calcular_salario'),
    
    # =================== API REST ===================
    # Inclui todas as rotas dos ViewSets
    path('timetrack/', include(router.urls)),
]