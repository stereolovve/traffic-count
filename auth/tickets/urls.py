from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'api', views.TicketViewSet)

urlpatterns = [
    # Views principais
    path('', views.ticket_list, name='ticket_list'),
    path('dashboard/', views.dashboard, name='ticket_dashboard'),
    path('create/', views.ticket_create, name='ticket_create'),
    path('<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('<int:pk>/edit/', views.ticket_edit, name='ticket_edit'),
    path('<int:pk>/delete/', views.ticket_delete, name='ticket_delete'),
    path('<int:pk>/change-status/', views.ticket_change_status, name='ticket_change_status'),
    path('<int:pk>/atribuir-pesquisador/', views.ticket_assign_researcher, name='ticket_assign_researcher'),
    
    # APIs para autocomplete
    path('api/codigos/', views.api_codigos, name='api_codigos'),
    path('api/padroes/', views.api_padroes, name='api_padroes'),
    path('api/pesquisadores/', views.api_pesquisadores, name='api_pesquisadores'),
    
    # API REST
    path('', include(router.urls)),
]
