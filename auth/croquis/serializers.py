from rest_framework import serializers
from .models import Croquis

class CroquisSerializer(serializers.ModelSerializer):
    codigo_nome = serializers.CharField(source='codigo.codigo', read_only=True)
    ponto_nome = serializers.CharField(source='ponto.nome', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Croquis
        fields = [
            'id', 'codigo', 'codigo_nome', 'ponto', 'ponto_nome', 
            'lote', 'movimento', 'data_croqui', 'hora_inicio', 'hora_fim',
            'imagem', 'status', 'status_display', 'observacao',
            'created_by', 'created_by_name', 'created_at',
            'aprovado_por', 'aprovado_em'
        ]
        read_only_fields = ['created_by', 'created_at', 'aprovado_por', 'aprovado_em']
