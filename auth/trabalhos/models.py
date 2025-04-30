#trabalhos/models.py
from django.db import models

# Create your models here.

class Cliente(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nome


class Codigo(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='codigos')
    codigo = models.CharField(max_length=20)
    descricao = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ('cliente', 'codigo')

    def __str__(self):
        return f"{self.codigo} ({self.cliente.nome})"


class Ponto(models.Model):
    codigo = models.ForeignKey(Codigo, on_delete=models.CASCADE, related_name='pontos')
    nome = models.CharField(max_length=100)
    localizacao = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        unique_together = ('codigo', 'nome')

    def __str__(self):
        return f"{self.nome} - {self.codigo.codigo} ({self.codigo.cliente.nome})"


# Modelos para Detalhes do Ponto
class PontoDetail(models.Model):
    ponto = models.ForeignKey(Ponto, on_delete=models.CASCADE, related_name='details')
    movimento = models.CharField(max_length=100)
    observacao = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class PontoDetailImage(models.Model):
    detail = models.ForeignKey(PontoDetail, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='ponto_details/')
