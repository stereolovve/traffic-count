# folha_ponto/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import UserProfile, WorkCode, TimeRecord, Salary
from autenticacao.models import User

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer para perfil do usuário"""
    
    class Meta:
        model = UserProfile
        fields = [
            'valor_hora', 'cargo', 'departamento', 'telefone', 
            'data_admissao', 'ativo', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class UserSerializer(serializers.ModelSerializer):
    """Serializer para dados do usuário com perfil"""
    profile = UserProfileSerializer(source='folha_ponto_profile', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'name', 'setor', 'profile'
        ]
        read_only_fields = ['id', 'username']

class UserRegistrationSerializer(serializers.Serializer):
    """Serializer para registro de novos usuários"""
    username = serializers.CharField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)
    valor_hora = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("As senhas não coincidem")
        
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError("Nome de usuário já existe")
        
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError("Email já está em uso")
        
        return attrs
    
    def create(self, validated_data):
        # Remove password_confirm do validated_data
        validated_data.pop('password_confirm')
        valor_hora = validated_data.pop('valor_hora')
        
        # Criar usuário
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            name=validated_data['first_name'],
            password=validated_data['password']
        )
        
        # Criar perfil
        UserProfile.objects.create(
            user=user,
            valor_hora=valor_hora
        )
        
        return user

class WorkCodeSerializer(serializers.ModelSerializer):
    """Serializer para códigos de trabalho"""
    codigo_trabalho_display = serializers.CharField(
        source='codigo_trabalho.__str__', 
        read_only=True
    )
    
    class Meta:
        model = WorkCode
        fields = [
            'id', 'codigo', 'descricao', 'ativo', 
            'codigo_trabalho', 'codigo_trabalho_display',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class TimeRecordSerializer(serializers.ModelSerializer):
    """Serializer para registros de ponto"""
    user_display = serializers.CharField(source='user.username', read_only=True)
    work_code_display = serializers.CharField(source='work_code.__str__', read_only=True)
    horas_trabalhadas = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True
    )
    horas_formatadas = serializers.CharField(read_only=True)
    valor_dia = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    aprovado_por_display = serializers.CharField(
        source='aprovado_por.username', read_only=True
    )
    
    class Meta:
        model = TimeRecord
        fields = [
            'id', 'user', 'user_display', 'data',
            'entrada1', 'saida1', 'entrada2', 'saida2', 'entrada3', 'saida3',
            'work_code', 'work_code_display', 'observacoes',
            'status', 'aprovado_por', 'aprovado_por_display', 'data_aprovacao',
            'sessao_contagem', 'horas_trabalhadas', 'horas_formatadas', 'valor_dia',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'aprovado_por', 'data_aprovacao', 
            'created_at', 'updated_at', 'horas_trabalhadas', 
            'horas_formatadas', 'valor_dia'
        ]
    
    def validate(self, attrs):
        """Validações customizadas"""
        # Validar que saída é maior que entrada
        if attrs.get('entrada1') and attrs.get('saida1'):
            if attrs['saida1'] <= attrs['entrada1']:
                raise serializers.ValidationError(
                    "Saída 1 deve ser posterior à Entrada 1"
                )
        
        if attrs.get('entrada2') and attrs.get('saida2'):
            if attrs['saida2'] <= attrs['entrada2']:
                raise serializers.ValidationError(
                    "Saída 2 deve ser posterior à Entrada 2"
                )
        
        if attrs.get('entrada3') and attrs.get('saida3'):
            if attrs['saida3'] <= attrs['entrada3']:
                raise serializers.ValidationError(
                    "Saída 3 deve ser posterior à Entrada 3"
                )
        
        return attrs

class TimeRecordCreateSerializer(TimeRecordSerializer):
    """Serializer específico para criação de registros"""
    
    def create(self, validated_data):
        # Definir usuário como o usuário autenticado
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class TimeRecordSupervisorSerializer(TimeRecordSerializer):
    """Serializer para supervisores (com campos adicionais)"""
    
    class Meta(TimeRecordSerializer.Meta):
        read_only_fields = [
            'id', 'created_at', 'updated_at', 
            'horas_trabalhadas', 'horas_formatadas', 'valor_dia'
        ]
    
    def update(self, instance, validated_data):
        # Supervisores podem alterar status e aprovar/rejeitar
        if 'status' in validated_data:
            if validated_data['status'] in ['aprovado', 'rejeitado']:
                validated_data['aprovado_por'] = self.context['request'].user
                validated_data['data_aprovacao'] = timezone.now()
        
        return super().update(instance, validated_data)

class SalarySerializer(serializers.ModelSerializer):
    """Serializer para histórico de salários"""
    user_display = serializers.CharField(source='user.username', read_only=True)
    mes_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Salary
        fields = [
            'id', 'user', 'user_display', 'ano', 'mes', 'mes_display',
            'horas_trabalhadas', 'valor_hora', 'total_bruto',
            'registros_aprovados', 'registros_pendentes', 'data_calculo'
        ]
        read_only_fields = ['id', 'data_calculo']
    
    def get_mes_display(self, obj):
        meses = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        return meses[obj.mes - 1]


class RelatorioMensalSerializer(serializers.Serializer):
    """Serializer para relatório mensal"""
    usuario = UserSerializer()
    ano = serializers.IntegerField()
    mes = serializers.IntegerField()
    mes_display = serializers.CharField()
    registros = TimeRecordSerializer(many=True)
    total_horas = serializers.DecimalField(max_digits=8, decimal_places=2)
    total_valor = serializers.DecimalField(max_digits=12, decimal_places=2)
    registros_aprovados = serializers.IntegerField()
    registros_pendentes = serializers.IntegerField()
    registros_rejeitados = serializers.IntegerField()