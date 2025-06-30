from rest_framework import serializers
from .models import Ticket
from autenticacao.models import User
from trabalhos.models import Codigo
from padroes.models import PadraoContagem

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'name', 'last_name', 'email', 'setor']

class CodigoSerializer(serializers.ModelSerializer):
    cliente_nome = serializers.CharField(source='cliente.nome', read_only=True)
    
    class Meta:
        model = Codigo
        fields = ['id', 'codigo', 'descricao', 'cliente_nome']

class PadraoContagemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PadraoContagem
        fields = ['id', 'pattern_type', 'veiculo', 'bind', 'order']

class TicketSerializer(serializers.ModelSerializer):
    coordenador = UserSerializer(read_only=True)
    pesquisador = UserSerializer(read_only=True)
    codigo = CodigoSerializer(read_only=True)
    padrao = PadraoContagemSerializer(read_only=True)
    
    coordenador_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(setor='SUPER'),
        source='coordenador',
        write_only=True,
        required=False
    )
    
    pesquisador_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='pesquisador',
        write_only=True,
        required=False,
        allow_null=True
    )
    
    codigo_id = serializers.PrimaryKeyRelatedField(
        queryset=Codigo.objects.all(),
        source='codigo',
        write_only=True
    )
    
    padrao_id = serializers.PrimaryKeyRelatedField(
        queryset=PadraoContagem.objects.all(),
        source='padrao',
        write_only=True
    )
    
    periodo_formatado = serializers.CharField(read_only=True)
    duracao_formatada = serializers.CharField(read_only=True)
    
    class Meta:
        model = Ticket
        fields = [
            'id', 'turno', 'coordenador', 'coordenador_id', 'codigo', 'codigo_id',
            'cam', 'mov', 'padrao', 'padrao_id', 'duracao', 'periodo_inicio',
            'periodo_fim', 'data', 'nivel', 'prioridade', 'observacao',
            'status', 'pesquisador', 'pesquisador_id', 'data_atribuicao',
            'data_finalizacao', 'criado_em', 'atualizado_em',
            'periodo_formatado', 'duracao_formatada'
        ]
        read_only_fields = [
            'id', 'criado_em', 'atualizado_em', 'data_atribuicao', 'data_finalizacao'
        ]
    
    def validate(self, data):
        periodo_inicio = data.get('periodo_inicio')
        periodo_fim = data.get('periodo_fim')
        
        if periodo_inicio and periodo_fim:
            if periodo_inicio >= periodo_fim:
                raise serializers.ValidationError(
                    'O horário de início deve ser anterior ao horário de fim.'
                )
        
        return data
    
    def validate_duracao(self, value):
        if value <= 0:
            raise serializers.ValidationError('A duração deve ser maior que zero.')
        return value
    
    def validate_nivel(self, value):
        if value < 1 or value > 10:
            raise serializers.ValidationError('O nível deve estar entre 1 e 10.')
        return value

class TicketListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listagem"""
    coordenador_nome = serializers.CharField(source='coordenador.username', read_only=True)
    pesquisador_nome = serializers.CharField(source='pesquisador.username', read_only=True)
    codigo_nome = serializers.CharField(source='codigo.codigo', read_only=True)
    padrao_nome = serializers.CharField(source='padrao.pattern_type', read_only=True)
    periodo_formatado = serializers.CharField(read_only=True)
    
    class Meta:
        model = Ticket
        fields = [
            'id', 'turno', 'data', 'periodo_formatado', 'coordenador_nome',
            'pesquisador_nome', 'codigo_nome', 'padrao_nome', 'status',
            'prioridade', 'nivel', 'criado_em'
        ]

class TicketStatusUpdateSerializer(serializers.Serializer):
    """Serializer para atualização de status"""
    status = serializers.ChoiceField(choices=Ticket.STATUS_CHOICES)
    
    def validate_status(self, value):
        if value not in dict(Ticket.STATUS_CHOICES):
            raise serializers.ValidationError('Status inválido.')
        return value

class TicketPesquisadorUpdateSerializer(serializers.Serializer):
    """Serializer para atribuição de pesquisador"""
    pesquisador_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='pesquisador'
    )
    
    def validate_pesquisador_id(self, value):
        if not value:
            raise serializers.ValidationError('Pesquisador é obrigatório.')
        return value 