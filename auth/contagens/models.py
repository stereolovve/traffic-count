#contagens/models.py
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone

class Session(models.Model):
    sessao = models.CharField(max_length=255, unique=True)
    pesquisador = models.CharField(max_length=255)
    codigo = models.CharField(max_length=100)
    ponto = models.CharField(max_length=255)
    horario_inicio = models.CharField(max_length=5, null=True, blank=True)
    horario_fim = models.CharField(max_length=5, null=True, blank=True)
    movimentos = models.JSONField(default=list)
    data = models.CharField(max_length=10, null=True, blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, default=1)
    status = models.CharField(
        max_length=20,
        choices=[
            ("Aguardando", "Aguardando"),
            ("Em andamento", "Em andamento"),
            ("Concluída", "Concluída"),
        ],
        default="Aguardando",
    )
    padrao = models.CharField(max_length=100, blank=True, null=True, help_text="Tipo de padrão utilizado na contagem")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def ativa(self):
        """Backward compatibility property for 'ativa' field"""
        return self.status == "Em andamento"
    
    def __str__(self):
        return f"{self.codigo} - {self.ponto} ({self.data})"

class Counting(models.Model):
    sessao = models.ForeignKey(Session, on_delete=models.CASCADE)
    veiculo = models.CharField(max_length=100)
    movimento = models.CharField(max_length=10)
    contagem = models.IntegerField(default=0)
    periodo = models.CharField(max_length=5, blank=True, null=True)  # Formato "HH:MM"
    
    class Meta:
        ordering = ['periodo', 'id']  # Ordenar por período e depois pelo ID

    def __str__(self):
        return f"{self.veiculo} - {self.movimento}: {self.contagem}"
