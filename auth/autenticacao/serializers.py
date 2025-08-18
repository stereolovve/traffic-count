# auth/autenticacao/serializers.py
from django.contrib.auth import get_user_model
from rest_framework import serializers
import re
from rest_framework.validators import ValidationError
from django.contrib.auth.password_validation import validate_password


Usuario = get_user_model()

class RegistroSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(write_only=True, min_length=8, label="Senha")
    password2 = serializers.CharField(write_only=True, min_length=8, label="Confirmação de Senha")
    setor = serializers.ChoiceField(choices=[
        ('CON', 'Contagem'),
        ('DIG', 'Digitação'),
        ('P&D', 'Perci'),
        ('SUPER', 'Supervisão'),
    ], required=True)
    
    class Meta:
        model = Usuario
        fields = ['id', 'username', 'password1', 'password2', 'name', 'last_name', 'email', 'setor']
        extra_kwargs = {
            'email': {'required': True},
            'name': {'required': True},
            'last_name': {'required': True},
            'setor': {'required': True},
        }
    
    def validate_username(self, value):
        if not re.match(r'^[a-zA-Z]+\.[a-zA-Z]+$', value):
            raise ValidationError("O username deve estar no formato nome.sobrenome.")
        return value
    
    def validate_email(self, value):
        if Usuario.objects.filter(email=value).exists():
            raise ValidationError('Este e-mail já está em uso.')
        return value
    
    def validate_password1(self, value):
        validate_password(value)
        return value
    
    def validate(self, data):
        if data['password1'] != data['password2']:
            raise ValidationError({'password2': 'As senhas não coincidem.'})
        return data
    
    def create(self, validated_data):
        # Remover password2 dos dados validados
        validated_data.pop('password2', None)
        password = validated_data.pop('password1')
        
        user = Usuario.objects.create_user(
            username=validated_data['username'],
            password=password,
            name=validated_data['name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
            setor=validated_data['setor']
        )
        return user

# Manter o serializer original para compatibilidade com API
class RegistroAPISerializer(serializers.ModelSerializer):
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


