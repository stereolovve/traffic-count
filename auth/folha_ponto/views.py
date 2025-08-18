# folha_ponto/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, date
from decimal import Decimal
import calendar

from .models import UserProfile, WorkCode, TimeRecord, Salary
from .serializers import (
    UserProfileSerializer, UserSerializer, UserRegistrationSerializer,
    WorkCodeSerializer, TimeRecordSerializer, TimeRecordCreateSerializer,
    TimeRecordSupervisorSerializer, SalarySerializer,
    RelatorioMensalSerializer
)

User = get_user_model()

# =================== AUTENTICAÇÃO ===================

@api_view(['POST'])
@permission_classes([AllowAny])
def folha_ponto_login(request):
    """Login específico para folha de ponto (compatível com sistema original)"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'detail': 'Username e password são obrigatórios'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(username=username, password=password)
    
    if user:
        refresh = RefreshToken.for_user(user)
        
        # Buscar ou criar perfil
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'profile': {
                    'cargo': profile.cargo,
                    'valor_hora': str(profile.valor_hora),
                    'departamento': profile.departamento,
                    'telefone': profile.telefone,
                    'data_admissao': profile.data_admissao,
                    'ativo': profile.ativo
                }
            }
        })
    
    return Response(
        {'detail': 'Credenciais inválidas'},
        status=status.HTTP_401_UNAUTHORIZED
    )

@api_view(['POST'])
@permission_classes([AllowAny])
def folha_ponto_register(request):
    """Registro específico para folha de ponto"""
    serializer = UserRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
            'message': 'Usuário criado com sucesso'
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    """Obter perfil do usuário autenticado"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    return Response(UserSerializer(request.user).data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user_profile(request):
    """Atualizar perfil do usuário autenticado"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    serializer = UserProfileSerializer(profile, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response(UserSerializer(request.user).data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_users(request):
    """Listar todos os usuários (apenas para supervisores)"""
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if not user_profile.is_supervisor:
        return Response(
            {'detail': 'Permissão negada'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    users = User.objects.all()
    return Response(UserSerializer(users, many=True).data)

# =================== WORK CODES ===================

class WorkCodeViewSet(viewsets.ModelViewSet):
    """ViewSet para códigos de trabalho"""
    serializer_class = WorkCodeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return WorkCode.objects.filter(ativo=True).order_by('codigo')

# =================== TIME RECORDS ===================

class TimeRecordViewSet(viewsets.ModelViewSet):
    """ViewSet para registros de ponto"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TimeRecordCreateSerializer
        
        # Verificar se é supervisor
        user_profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        if user_profile.is_supervisor:
            return TimeRecordSupervisorSerializer
        
        return TimeRecordSerializer
    
    def get_queryset(self):
        user = self.request.user
        user_profile, created = UserProfile.objects.get_or_create(user=user)
        
        queryset = TimeRecord.objects.select_related('user', 'work_code', 'aprovado_por')
        
        # Filtros por query params
        mes = self.request.query_params.get('mes')
        ano = self.request.query_params.get('ano')
        user_id = self.request.query_params.get('user_id')
        
        # Se é supervisor, pode ver todos os registros
        if user_profile.is_supervisor:
            if user_id:
                queryset = queryset.filter(user_id=user_id)
        else:
            # Usuários comuns só veem seus próprios registros
            queryset = queryset.filter(user=user)
        
        # Filtros de data
        if ano:
            queryset = queryset.filter(data__year=ano)
        if mes:
            queryset = queryset.filter(data__month=mes)
        
        return queryset.order_by('-data')
    
    @action(detail=False, methods=['get'])
    def supervisor(self, request):
        """Endpoint específico para supervisores visualizarem registros de outros usuários"""
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        if not user_profile.is_supervisor:
            return Response(
                {'detail': 'Permissão negada'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# =================== RELATÓRIOS ===================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def relatorio_mensal(request, ano, mes):
    """Relatório mensal detalhado"""
    user = request.user
    
    # Supervisores podem ver relatórios de outros usuários
    user_profile, created = UserProfile.objects.get_or_create(user=user)
    target_user_id = request.query_params.get('user_id')
    
    if target_user_id and user_profile.is_supervisor:
        try:
            target_user = User.objects.get(id=target_user_id)
        except User.DoesNotExist:
            return Response(
                {'detail': 'Usuário não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        target_user = user
    
    # Buscar registros do mês
    registros = TimeRecord.objects.filter(
        user=target_user,
        data__year=ano,
        data__month=mes
    ).order_by('data')
    
    # Calcular totais
    total_horas = sum(r.horas_trabalhadas for r in registros)
    
    target_profile, created = UserProfile.objects.get_or_create(user=target_user)
    total_valor = total_horas * target_profile.valor_hora
    
    registros_aprovados = registros.filter(status='aprovado').count()
    registros_pendentes = registros.filter(status='pendente').count()
    registros_rejeitados = registros.filter(status='rejeitado').count()
    
    # Nome do mês
    meses = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    
    data = {
        'usuario': UserSerializer(target_user).data,
        'ano': ano,
        'mes': mes,
        'mes_display': meses[mes - 1],
        'registros': TimeRecordSerializer(registros, many=True).data,
        'total_horas': total_horas,
        'total_valor': total_valor,
        'registros_aprovados': registros_aprovados,
        'registros_pendentes': registros_pendentes,
        'registros_rejeitados': registros_rejeitados
    }
    
    return Response(data)

# =================== SALÁRIOS ===================

class SalaryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para histórico de salários"""
    serializer_class = SalarySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        user_profile, created = UserProfile.objects.get_or_create(user=user)
        
        if user_profile.is_supervisor:
            return Salary.objects.all().order_by('-ano', '-mes')
        
        return Salary.objects.filter(user=user).order_by('-ano', '-mes')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calcular_salario_mensal(request):
    """Calcular e salvar salário de um mês específico"""
    user = request.user
    ano = request.data.get('ano')
    mes = request.data.get('mes')
    
    if not ano or not mes:
        return Response(
            {'detail': 'Ano e mês são obrigatórios'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Buscar registros do mês
    registros = TimeRecord.objects.filter(
        user=user,
        data__year=ano,
        data__month=mes
    )
    
    # Calcular métricas
    total_horas = sum(r.horas_trabalhadas for r in registros)
    registros_aprovados = registros.filter(status='aprovado').count()
    registros_pendentes = registros.filter(status='pendente').count()
    
    profile, created = UserProfile.objects.get_or_create(user=user)
    total_bruto = total_horas * profile.valor_hora
    
    # Criar ou atualizar registro de salário
    salary, created = Salary.objects.update_or_create(
        user=user,
        ano=ano,
        mes=mes,
        defaults={
            'horas_trabalhadas': total_horas,
            'valor_hora': profile.valor_hora,
            'total_bruto': total_bruto,
            'registros_aprovados': registros_aprovados,
            'registros_pendentes': registros_pendentes
        }
    )
    
    return Response(
        SalarySerializer(salary).data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
    )