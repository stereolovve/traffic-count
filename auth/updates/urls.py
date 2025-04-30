# auth/updates/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.updates_page, name='updates_page'),
    path('api/check-version/', views.check_version, name='check_version'),
]
