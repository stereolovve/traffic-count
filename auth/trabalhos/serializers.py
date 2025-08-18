from rest_framework import serializers
from .models import Cliente, Codigo, Ponto, PontoDetail, PontoDetailImage

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

class PontoDetailImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PontoDetailImage
        fields = ['id', 'image']

class PontoDetailSerializer(serializers.ModelSerializer):
    images = PontoDetailImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        allow_empty=True
    )

    class Meta:
        model = PontoDetail
        fields = ['id', 'ponto', 'movimento', 'observacao', 'created_at', 'images', 'uploaded_images']
        read_only_fields = ['created_at']

    def validate(self, data):
        movimento = data.get('movimento', '').strip()
        observacao = data.get('observacao', '').strip()
        uploaded_images = data.get('uploaded_images', [])
        
        if not movimento and not observacao and not uploaded_images:
            raise serializers.ValidationError(
                "Pelo menos um campo deve ser preenchido: movimento, observação ou imagens."
            )
        
        return data

    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        
        detail = PontoDetail.objects.create(**validated_data)
        
        for image in uploaded_images:
            PontoDetailImage.objects.create(detail=detail, image=image)
        
        return detail 