# auth/padroes/serializers.py
from rest_framework import serializers
from .models import PadraoContagem, UserPadraoContagem

class PadraoContagemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PadraoContagem
        fields = '__all__'

class UserPadraoContagemSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPadraoContagem
        fields = '__all__'
        read_only_fields = ['user']