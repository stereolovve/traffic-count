# auth/updates/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.updates_page, name='updates_page'),
    
    # API endpoints públicos
    path('api/check-version/', views.check_version, name='check_version'),
    path('api/download/', views.download_latest, name='download_latest'),
    path('api/history/', views.version_history, name='version_history'),
    
    # API endpoints privados (staff only)
    path('api/upload/', views.upload_release, name='upload_release'),
]
