# auth/autenticacao/serializers.py
from django.contrib.auth import get_user_model
from rest_framework import serializers
import re
from rest_framework.validators import ValidationError


Usuario = get_user_model()

class RegistroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'username', 'password', 'name','last_name', 'email', 'setor']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
            'name': {'required': True},
            'last_name': {'required': True},
            'setor': {'required': True},
        }
    
    def validate_username(self, value):
        if not re.match(r'^[a-zA-Z]+\.[a-zA-Z]+$', value):
            raise ValidationError("O username deve estar no formato nome.sobrenome.")
        return value
    
    def create(self, validated_data):
        user = Usuario.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            name=validated_data['name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
            setor=validated_data['setor']
        )
        return user


