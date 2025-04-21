from django.urls import path
from . import views

urlpatterns = [
    path('', views.CroquisListView.as_view(), name='croquis_list'),
    path('<int:pk>/', views.CroquisDetailView.as_view(), name='croquis_detail'),
    path('new/', views.CroquisCreateView.as_view(), name='croquis_create'),
    path('<int:pk>/edit/', views.CroquisUpdateView.as_view(), name='croquis_edit'),
    path('<int:pk>/delete/', views.CroquisDeleteView.as_view(), name='croquis_delete'),
    path('<int:pk>/review/', views.CroquisReviewView.as_view(), name='croquis_review'),
    path('ajax/load-pontos/', views.ajax_load_pontos, name='ajax_load_pontos'),
]
