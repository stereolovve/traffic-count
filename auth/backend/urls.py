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
from django.contrib.auth import views as auth_views
from autenticacao import views as auth_views_custom
from contagens import views
from padroes import views
from autenticacao.models import User
from contagens.models import Session, Counting
from trabalhos.models import Cliente, Codigo
from django.db.models import Count
from django.conf import settings
from django.conf.urls.static import static

def home(request):
    if request.user.is_authenticated:
        # Get session statistics
        sessoes_ativas = Session.objects.filter(status="Em andamento").count()
        sessoes_finalizadas = Session.objects.filter(status="Concluída").count()
        total_sessoes = Session.objects.count()
        total_usuarios = User.objects.count()
        
        # Top users with most sessions
        top_usuarios = User.objects.annotate(
            count=Count('session')  # Using the correct reverse relation name
        ).order_by('-count')[:5]
        
        # Top codes with most sessions
        codigos_com_mais_sessoes = Session.objects.values('codigo').annotate(
            total_sessoes=Count('id')
        ).order_by('-total_sessoes')[:5]
        
        # Get clients with most sessions (through codes)
        # First get all códigos from sessions, then group by client name
        clientes_com_mais_sessoes = []
        try:
            # Get all sessions with their códigos
            session_codigos = Session.objects.values_list('codigo', flat=True)
            
            # Count sessions per client by matching códigos
            cliente_counts = {}
            for session_codigo in session_codigos:
                # Find the codigo object and its client
                try:
                    codigo_obj = Codigo.objects.get(codigo=session_codigo)
                    cliente_name = codigo_obj.cliente.nome
                    cliente_counts[cliente_name] = cliente_counts.get(cliente_name, 0) + 1
                except Codigo.DoesNotExist:
                    # If código doesn't exist in trabalhos, skip
                    continue
            
            # Convert to list and sort by count
            clientes_com_mais_sessoes = [
                {'cliente': nome, 'total_sessoes': count}
                for nome, count in sorted(cliente_counts.items(), key=lambda x: x[1], reverse=True)
            ][:5]
        except Exception:
            # In case of any error, return empty list
            clientes_com_mais_sessoes = []
        
        # Most recent sessions
        sessoes_recentes = Session.objects.all().order_by('-id')[:5]  # Using 'id' as a fallback, use your date field instead
        
        context = {
            'sessoes_ativas': sessoes_ativas,
            'sessoes_finalizadas': sessoes_finalizadas,
            'total_sessoes': total_sessoes,
            'total_usuarios': total_usuarios,
            'top_usuarios': top_usuarios,
            'codigos_com_mais_sessoes': codigos_com_mais_sessoes,
            'clientes_com_mais_sessoes': clientes_com_mais_sessoes,
            'sessoes_recentes': sessoes_recentes,
        }
        
        return render(request, 'auth/home.html', context)
    return render(request, 'auth/home.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('autenticacao.urls')),
    path('', home, name='home'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/auth/login/'), name='logout'),
    path('register/', auth_views_custom.register, name='register'),
    path('contagens/', include('contagens.urls')),
    path('padroes/', include('padroes.urls')),
    path('trabalhos/', include('trabalhos.urls')),
    path('updates/', include('updates.urls')),
    path('tickets/', include('tickets.urls')),
    path('api/', include('folha_ponto.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
