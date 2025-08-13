# auth/updates/views.py
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import re
import logging
from .models import Release

logger = logging.getLogger(__name__)

def compare_versions(v1, v2):
    """
    Compara duas versões no formato semver (x.y.z)
    Retorna: -1 se v1 < v2, 0 se v1 == v2, 1 se v1 > v2
    """
    def normalize_version(v):
        # Remove 'v' prefix se existir e divide em números
        clean_v = v.strip().lstrip('v').split('.')
        return [int(x) for x in clean_v if x.isdigit()]
    
    try:
        v1_parts = normalize_version(v1)
        v2_parts = normalize_version(v2)
        
        # Preencher com zeros para ter mesmo tamanho
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts += [0] * (max_len - len(v1_parts))
        v2_parts += [0] * (max_len - len(v2_parts))
        
        for i in range(max_len):
            if v1_parts[i] < v2_parts[i]:
                return -1
            elif v1_parts[i] > v2_parts[i]:
                return 1
        return 0
    except (ValueError, AttributeError):
        # Se não conseguir comparar, assume que são diferentes
        return -1 if v1 != v2 else 0

def updates_page(request):
    """Página web para gerenciar updates"""
    latest = Release.objects.first()
    all_releases = Release.objects.all()[:10]  # Últimas 10 versões
    
    return render(request, 'updates/updates.html', {
        'release': latest,
        'all_releases': all_releases,
    })

@api_view(['GET'])
def check_version(request):
    """
    API endpoint para verificar a versão mais recente disponível
    Parâmetros:
    - version: versão atual do cliente
    - platform: plataforma do cliente (opcional)
    """
    try:
        current_version = request.GET.get('version', '0.0.0')
        platform = request.GET.get('platform', 'windows')
        
        logger.info(f"Check version request: current={current_version}, platform={platform}")
        
        latest_release = Release.objects.first()
        
        if not latest_release:
            return JsonResponse({
                'has_update': False,
                'message': 'Nenhuma versão disponível',
                'current_version': current_version
            })
        
        # Usar comparação semver
        version_comparison = compare_versions(current_version, latest_release.version)
        has_update = version_comparison < 0
        
        response_data = {
            'has_update': has_update,
            'current_version': current_version,
            'latest_version': latest_release.version,
            'comparison_result': version_comparison,
        }
        
        if has_update:
            response_data.update({
                'download_url': request.build_absolute_uri(latest_release.file.url),
                'changelog': latest_release.changelog,
                'published_at': latest_release.published_at.strftime('%d/%m/%Y %H:%M'),
                'file_size': latest_release.file.size if latest_release.file else 0,
                'update_required': version_comparison < -1,  # Update obrigatório se muito desatualizado
            })
        
        logger.info(f"Check version response: has_update={has_update}")
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error in check_version: {str(e)}")
        return JsonResponse({
            'error': 'Erro interno do servidor',
            'has_update': False
        }, status=500)

@api_view(['GET'])
def download_latest(request):
    """
    Endpoint para download direto da versão mais recente
    """
    try:
        latest_release = Release.objects.first()
        
        if not latest_release or not latest_release.file:
            raise Http404("Arquivo não encontrado")
        
        # Log do download
        user_info = f"user:{request.user.id}" if request.user.is_authenticated else "anonymous"
        logger.info(f"Download iniciado - {user_info} - version:{latest_release.version}")
        
        # Redirecionar para o arquivo
        return HttpResponse(
            status=302,
            headers={'Location': latest_release.file.url}
        )
        
    except Exception as e:
        logger.error(f"Error in download_latest: {str(e)}")
        return JsonResponse({'error': 'Arquivo não encontrado'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_release(request):
    """
    Endpoint para upload de nova versão (apenas para usuários autenticados)
    """
    try:
        if not request.user.is_staff:
            return JsonResponse({'error': 'Permissão negada'}, status=403)
        
        version = request.POST.get('version')
        changelog = request.POST.get('changelog', '')
        file_obj = request.FILES.get('file')
        
        if not version or not file_obj:
            return JsonResponse({
                'error': 'Versão e arquivo são obrigatórios'
            }, status=400)
        
        # Verificar se versão já existe
        if Release.objects.filter(version=version).exists():
            return JsonResponse({
                'error': f'Versão {version} já existe'
            }, status=400)
        
        # Criar novo release
        release = Release.objects.create(
            version=version,
            changelog=changelog,
            file=file_obj
        )
        
        logger.info(f"Nova versão criada: {version} por {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'version': release.version,
            'id': release.id,
            'download_url': request.build_absolute_uri(release.file.url)
        })
        
    except Exception as e:
        logger.error(f"Error in upload_release: {str(e)}")
        return JsonResponse({'error': 'Erro interno'}, status=500)

@api_view(['GET'])
def version_history(request):
    """
    Endpoint para obter histórico de versões
    """
    try:
        limit = min(int(request.GET.get('limit', 10)), 50)  # Máximo 50
        releases = Release.objects.all()[:limit]
        
        data = []
        for release in releases:
            data.append({
                'version': release.version,
                'changelog': release.changelog,
                'published_at': release.published_at.strftime('%d/%m/%Y %H:%M'),
                'file_size': release.file.size if release.file else 0
            })
        
        return JsonResponse({
            'releases': data,
            'total': Release.objects.count()
        })
        
    except Exception as e:
        logger.error(f"Error in version_history: {str(e)}")
        return JsonResponse({'error': 'Erro interno'}, status=500)
