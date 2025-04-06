"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# backend/urls.py
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.shortcuts import render
from contagens import views
from padroes import views
from autenticacao.models import User
from contagens.models import Session, Counting
from django.db.models import Count

def home(request):
    # Get session statistics
    sessoes_ativas = Session.objects.filter(ativa=True).count()
    sessoes_finalizadas = Session.objects.filter(ativa=False).count()
    total_usuarios = User.objects.count()
    
    # Top users with most sessions
    top_usuarios = User.objects.annotate(
        count=Count('session')  # Make sure 'sessao' is the correct related_name
    ).order_by('-count')[:5]
    
    # Most recent sessions
    sessoes_recentes = Session.objects.all().order_by('-id')[:5]  # Using 'id' as a fallback, use your date field instead
    
    context = {
        'sessoes_ativas': sessoes_ativas,
        'sessoes_finalizadas': sessoes_finalizadas,
        'total_usuarios': total_usuarios,
        'top_usuarios': top_usuarios,
        'sessoes_recentes': sessoes_recentes,
    }
    
    return render(request, 'auth/home.html', context)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('autenticacao.urls')),
    path('', home, name='home'),
    path('contagens/', include('contagens.urls')),
    path('padroes/', include('padroes.urls')),
]
