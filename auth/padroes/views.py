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

from .models import PadraoContagem, UserPadraoContagem
from .serializers import PadraoContagemSerializer, UserPadraoContagemSerializer
from .forms import PadraoContagemForm


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

class PadraoContagemCreateView(CreateView):
    model = PadraoContagem
    form_class = PadraoContagemForm
    template_name = 'padroes/padrao_form.html'
    success_url = reverse_lazy('padrao_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tipos_padroes'] = PadraoContagem.objects.values_list('pattern_type', flat=True).distinct()
        return context
    
    def post(self, request, *args, **kwargs):
        # Debug
        print("Form data:", request.POST)
        
        # Verificar se é o formulário múltiplo
        if 'pattern_type_final' in request.POST:
            pattern_type = request.POST.get('pattern_type_final')
            veiculos = request.POST.getlist('veiculo[]')
            binds = request.POST.getlist('bind[]')
            
            print(f"Criando padrões múltiplos: tipo={pattern_type}, veículos={veiculos}, binds={binds}")
            
            if not pattern_type or len(veiculos) == 0:
                messages.error(request, "Erro: Tipo de padrão e pelo menos um veículo são obrigatórios.")
                return redirect('padrao_create')
            
            # Criar padrões em massa
            count = 0
            for i, (veiculo, bind) in enumerate(zip(veiculos, binds)):
                if not veiculo or not bind:
                    continue
                    
                try:
                    # Calcular ordem baseada na posição
                    order = (i + 1) * 10
                    
                    # Verificar se já existe um padrão igual
                    existing = PadraoContagem.objects.filter(
                        pattern_type=pattern_type,
                        veiculo=veiculo
                    ).first()
                    
                    if existing:
                        # Atualizar existente
                        existing.bind = bind
                        existing.order = order
                        existing.save()
                    else:
                        # Criar novo
                        PadraoContagem.objects.create(
                            pattern_type=pattern_type,
                            veiculo=veiculo,
                            bind=bind,
                            order=order
                        )
                    count += 1
                except Exception as e:
                    messages.error(request, f"Erro ao salvar o padrão {veiculo}: {str(e)}")
            
            if count > 0:
                messages.success(request, f"{count} padrões foram salvos com sucesso!")
            
            return redirect('padrao_list')
            
        # Caso seja o formulário padrão (para edição de um único padrão)
        return super().post(request, *args, **kwargs)

class PadraoContagemUpdateView(UpdateView):
    model = PadraoContagem
    form_class = PadraoContagemForm
    template_name = 'padroes/padrao_form.html'
    success_url = reverse_lazy('padrao_list')

class PadraoContagemDeleteView(DeleteView):
    model = PadraoContagem
    template_name = 'padroes/padrao_confirm_delete.html'
    success_url = reverse_lazy('padrao_list')
    
# API Views
@api_view(['GET'])
def listar_tipos_padrao(request):
    tipos = PadraoContagem.objects.values_list('pattern_type', flat=True).distinct()
    return Response(list(tipos))

@api_view(['GET'])
@permission_classes([AllowAny])
def listar_padroes_globais(request):
    padroes = PadraoContagem.objects.values('pattern_type').distinct()
    data = []

    for padrao in padroes:
        tipo_padrao = padrao["pattern_type"]
        binds = PadraoContagem.objects.filter(pattern_type=tipo_padrao).values("veiculo", "bind")
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
def reorder_patterns(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método não permitido"}, status=405)
    
    try:
        data = json.loads(request.body)
        for item in data:
            PadraoContagem.objects.filter(id=item['id']).update(order=item['order'])
        return JsonResponse({"status": "success"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)