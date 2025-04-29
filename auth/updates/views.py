# auth/updates/views.py
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.decorators import api_view
from .models import Release

def updates_page(request):
    latest = Release.objects.first()  # graças ao ordering, pega a mais recente
    return render(request, 'updates/updates.html', {
        'release': latest,
    })

@api_view(['GET'])
def check_version(request):
    """API endpoint para verificar a versão mais recente disponível"""
    try:
        current_version = request.GET.get('version', '0.0.0')
        latest_release = Release.objects.first()  # Pega a versão mais recente
        
        if not latest_release:
            return JsonResponse({
                'has_update': False,
                'message': 'Nenhuma versão disponível'
            })
            
        # Comparação simples de versão (pode ser melhorada para comparar semver)
        has_update = latest_release.version != current_version
        
        return JsonResponse({
            'has_update': has_update,
            'latest_version': latest_release.version,
            'download_url': request.build_absolute_uri(latest_release.file.url) if has_update else None,
            'changelog': latest_release.changelog if has_update else None,
            'published_at': latest_release.published_at.strftime('%d/%m/%Y %H:%M') if has_update else None
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)
