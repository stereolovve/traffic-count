from django.shortcuts import render
from rest_framework import viewsets, filters
from .models import Cliente, Codigo, Ponto
from .serializers import ClienteSerializer, CodigoSerializer, PontoSerializer
from django_filters.rest_framework import DjangoFilterBackend

# Create your views here.

class ClienteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer

class CodigoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Codigo.objects.select_related('cliente').all()
    serializer_class = CodigoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['cliente']

class PontoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ponto.objects.select_related('codigo', 'codigo__cliente').all()
    serializer_class = PontoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['codigo']
