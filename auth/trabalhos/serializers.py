from rest_framework import serializers
from .models import Cliente, Codigo, Ponto

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'

class CodigoSerializer(serializers.ModelSerializer):
    cliente_nome = serializers.CharField(source='cliente.nome', read_only=True)

    class Meta:
        model = Codigo
        fields = ['id', 'codigo', 'descricao', 'cliente', 'cliente_nome']

class PontoSerializer(serializers.ModelSerializer):
    codigo_info = CodigoSerializer(source='codigo', read_only=True)

    class Meta:
        model = Ponto
        fields = ['id', 'nome', 'localizacao', 'codigo', 'codigo_info'] 