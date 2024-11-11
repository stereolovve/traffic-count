from django.contrib.auth import get_user_model
from rest_framework import serializers

Usuario = get_user_model()

class RegistroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'username', 'password', 'nome_completo', 'email', 'setor']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
            'nome_completo': {'required': True},
            'setor': {'required': True},
        }

    def create(self, validated_data):
        # Criação do usuário com senha hash
        user = Usuario.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            nome_completo=validated_data['nome_completo'],
            email=validated_data['email'],
            setor=validated_data['setor']
        )
        return user
