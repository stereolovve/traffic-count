from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
import json
from django.db import transaction

from .models import PadraoContagem, UserPadraoContagem
from .serializers import PadraoContagemSerializer, UserPadraoContagemSerializer
from .validators import PadraoValidator, UserPadraoValidator, ValidationResult


# ViewSets
class PadraoContagemViewSet(viewsets.ModelViewSet):
    serializer_class = PadraoContagemSerializer

    def get_queryset(self):
        queryset = PadraoContagem.objects.all()
        pattern_type = self.request.query_params.get('pattern_type', None)
        
        if pattern_type:
            queryset = queryset.filter(pattern_type=pattern_type)
            
        return queryset

class UserPadraoContagemViewSet(viewsets.ModelViewSet):
    serializer_class = UserPadraoContagemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserPadraoContagem.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        pattern_type = self.request.data.get("pattern_type")
        veiculo = self.request.data.get("veiculo")
        novo_bind = self.request.data.get("bind")

        if not (pattern_type and veiculo and novo_bind):
            raise serializers.ValidationError({"error": "Dados incompletos para salvar o bind."})

        try:
            bind_existente = UserPadraoContagem.objects.get(
                user=user, pattern_type=pattern_type, veiculo=veiculo
            )
            bind_existente.bind = novo_bind
            bind_existente.save()
            return
        except UserPadraoContagem.DoesNotExist:
            serializer.save(user=user)

# Class-based Views
class PadraoContagemListView(ListView):
    model = PadraoContagem
    template_name = 'padroes/padrao_list.html'
    context_object_name = 'padroes'
    
    def get_queryset(self):
        queryset = PadraoContagem.objects.all()
        self.selected_type = self.request.GET.get('pattern_type')
        
        if self.selected_type:
            queryset = queryset.filter(pattern_type=self.selected_type)
            # Ordenar por ordem para garantir consistência
            queryset = queryset.order_by('order', 'id')
        else:
            # Se estiver mostrando todos, ordenar por tipo primeiro, depois por ordem
            queryset = queryset.order_by('pattern_type', 'order', 'id')
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Usar set() para garantir que não há duplicatas
        tipos_padroes = set(PadraoContagem.objects.values_list('pattern_type', flat=True))
        context['tipos_padroes'] = sorted(tipos_padroes)  # Ordenar para exibição consistente
        context['selected_type'] = self.selected_type if hasattr(self, 'selected_type') else None
        return context

def padrao_create(request):
    if request.method == 'POST':
        # Verificar se é o formulário múltiplo
        if 'pattern_type_final' in request.POST:
            pattern_type = request.POST.get('pattern_type_final', '').strip()
            veiculos = [v.strip() for v in request.POST.getlist('veiculo[]') if v.strip()]
            binds = [b.strip() for b in request.POST.getlist('bind[]') if b.strip()]
            
            # Usar validador para criação múltipla
            errors = PadraoValidator.validate_multiple_data(pattern_type, veiculos, binds)
            
            if not errors:
                count = 0
                with transaction.atomic():
                    for i, (veiculo, bind) in enumerate(zip(veiculos, binds)):
                        try:
                            order = (i + 1) * 10
                            
                            # Verificar se já existe
                            existing = PadraoContagem.objects.filter(
                                pattern_type=pattern_type,
                                veiculo=veiculo
                            ).first()
                            
                            if existing:
                                existing.bind = bind
                                existing.order = order
                                existing.save()
                            else:
                                PadraoContagem.objects.create(
                                    pattern_type=pattern_type,
                                    veiculo=veiculo,
                                    bind=bind,
                                    order=order
                                )
                            count += 1
                            
                        except Exception as e:
                            messages.error(request, f'Erro ao processar {veiculo}: {str(e)}')
                
                if count > 0:
                    messages.success(request, f'{count} padrões foram salvos com sucesso!')
                    
                return redirect('padrao_list')
            else:
                # Exibir erros
                for error_list in errors.values():
                    if isinstance(error_list, list):
                        for error in error_list:
                            messages.error(request, error)
                    else:
                        messages.error(request, error_list)
        
        else:
            # Formulário individual
            data = {
                'pattern_type': request.POST.get('pattern_type', '').strip(),
                'veiculo': request.POST.get('veiculo', '').strip(),
                'bind': request.POST.get('bind', '').strip(),
                'order': request.POST.get('order', 0),
            }
            
            # Usar serializer para validação
            serializer = PadraoContagemSerializer(data=data)
            
            if serializer.is_valid():
                try:
                    serializer.save()
                    messages.success(request, 'Padrão criado com sucesso!')
                    return redirect('padrao_list')
                except Exception as e:
                    messages.error(request, f'Erro ao salvar: {str(e)}')
            else:
                # Exibir erros de validação
                for field, errors in serializer.errors.items():
                    for error in errors:
                        messages.error(request, f'{error}')
    
    # Preparar context para o template
    tipos_padroes = PadraoContagem.objects.values_list('pattern_type', flat=True).distinct()
    
    return render(request, 'padroes/padrao_form.html', {
        'tipos_padroes': tipos_padroes,
    })

def padrao_update(request, pk):
    padrao = get_object_or_404(PadraoContagem, pk=pk)
    
    if request.method == 'POST':
        data = {
            'pattern_type': request.POST.get('pattern_type', '').strip(),
            'veiculo': request.POST.get('veiculo', '').strip(),
            'bind': request.POST.get('bind', '').strip(),
            'order': request.POST.get('order', padrao.order),
        }
        
        # Usar serializer para validação e atualização
        serializer = PadraoContagemSerializer(padrao, data=data)
        
        if serializer.is_valid():
            try:
                serializer.save()
                messages.success(request, 'Padrão atualizado com sucesso!')
                return redirect('padrao_list')
            except Exception as e:
                messages.error(request, f'Erro ao salvar: {str(e)}')
        else:
            # Exibir erros de validação
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    
    # Preparar context para o template
    tipos_padroes = PadraoContagem.objects.values_list('pattern_type', flat=True).distinct()
    
    return render(request, 'padroes/padrao_form.html', {
        'object': padrao,
        'tipos_padroes': tipos_padroes,
    })

class PadraoContagemDeleteView(DeleteView):
    model = PadraoContagem
    template_name = 'padroes/padrao_confirm_delete.html'
    success_url = reverse_lazy('padrao_list')
    
# API Views
@api_view(['GET'])
def listar_tipos_padrao(request):
    # Usar distinct() para garantir que não há duplicatas
    tipos = PadraoContagem.objects.values_list('pattern_type', flat=True).distinct().order_by('pattern_type')
    return Response(list(tipos))

@api_view(['GET'])
@permission_classes([AllowAny])
def listar_padroes_globais(request):
    # Usar distinct() para garantir que não há duplicatas nos tipos de padrão
    padroes = PadraoContagem.objects.values('pattern_type').distinct().order_by('pattern_type')
    data = []

    for padrao in padroes:
        tipo_padrao = padrao["pattern_type"]
        # Obter os binds únicos para cada tipo de padrão
        binds = PadraoContagem.objects.filter(pattern_type=tipo_padrao).values("veiculo", "bind").distinct()
        data.append({
            "pattern_type": tipo_padrao,
            "binds": list(binds)
        })

    return Response(data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_or_global_padrao(request):
    if not request.user.is_authenticated:
        return Response({"detail": "Usuário não autenticado!"}, status=401)

    tipo = request.query_params.get('pattern_type')
    if not tipo:
        return Response({"detail": "Faltou o parâmetro pattern_type"}, status=400)

    globais = PadraoContagem.objects.filter(pattern_type=tipo)
    user_custom = UserPadraoContagem.objects.filter(user=request.user, pattern_type=tipo)

    global_dict = {g.veiculo: g.bind for g in globais}
    user_dict = {u.veiculo: u.bind for u in user_custom}

    merged = []
    for veiculo, bind_global in global_dict.items():
        bind_final = user_dict.get(veiculo, bind_global)
        merged.append({"veiculo": veiculo, "bind": bind_final, "pattern_type": tipo})

    for veiculo_user, bind_user in user_dict.items():
        if veiculo_user not in global_dict:
            merged.append({"veiculo": veiculo_user, "bind": bind_user, "pattern_type": tipo})

    return Response(merged, status=200)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_info(request):
    """Retorna informações básicas do usuário autenticado."""
    user = request.user
    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "preferences": user.preferences
    }, status=200)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_preferences_usuario(request):
    """Retorna os padrões personalizados do usuário ou os padrões globais."""
    user = request.user
    preferences = user.preferences if hasattr(user, 'preferences') else {}

    if not preferences:
        tipos_padroes = PadraoContagem.objects.values_list('pattern_type', flat=True).distinct()
        return Response(list(tipos_padroes), status=status.HTTP_200_OK)

    return Response(preferences, status=status.HTTP_200_OK)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def atualizar_preferences_usuario(request):
    user = request.user
    pattern_type = request.data.get("pattern_type")
    veiculo = request.data.get("veiculo")
    novo_bind = request.data.get("bind")

    if not pattern_type or not veiculo or not novo_bind:
        return Response({"detail": "Todos os campos são obrigatórios!"}, status=status.HTTP_400_BAD_REQUEST)

    preferences = user.preferences
    if pattern_type not in preferences:
        preferences[pattern_type] = {}

    preferences[pattern_type][veiculo] = novo_bind
    user.preferences = preferences
    user.save()

    return Response({"detail": "Bind atualizado com sucesso!"}, status=status.HTTP_200_OK)

@csrf_exempt
@require_POST
def reorder_patterns(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método não permitido"}, status=405)
    
    try:
        data = json.loads(request.body)
        pattern_type = data.get('pattern_type')
        patterns = data.get('patterns', [])
        
        if not pattern_type:
            return JsonResponse({
                "status": "error",
                "message": "Tipo de padrão não especificado"
            }, status=400)
            
        if not patterns:
            return JsonResponse({
                "status": "error",
                "message": "Nenhum padrão para reordenar"
            }, status=400)
        
        with transaction.atomic():
            # Get all patterns of this type to ensure we're only updating the correct ones
            existing_patterns = PadraoContagem.objects.filter(pattern_type=pattern_type)
            pattern_ids = [p['id'] for p in patterns]
            
            # Verify all patterns exist and belong to the specified type
            if existing_patterns.filter(id__in=pattern_ids).count() != len(pattern_ids):
                return JsonResponse({
                    "status": "error",
                    "message": "Um ou mais padrões não encontrados para o tipo especificado"
                }, status=404)
            
            # Update order for each pattern
            for item in patterns:
                pattern = existing_patterns.get(id=item['id'])
                pattern.order = item['order']
                pattern.save()
                
        return JsonResponse({
            "status": "success",
            "message": "Ordem atualizada com sucesso"
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            "status": "error",
            "message": "Formato de dados inválido"
        }, status=400)
    except PadraoContagem.DoesNotExist:
        return JsonResponse({
            "status": "error",
            "message": "Padrão não encontrado"
        }, status=404)
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"Erro ao reordenar padrões: {str(e)}"
        }, status=500)