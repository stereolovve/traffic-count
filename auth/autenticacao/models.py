# auth/autenticacao/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.conf import settings
import json


class User(AbstractUser):
    name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    setor = models.CharField(max_length=5, choices=[
        ('CON', 'Contagem'),
        ('DIG', 'Digitação'),
        ('P&D', 'Perci'),
        ('SUPER', 'Supervisao'),
    ], default='CON')

    preferences = models.JSONField(default=dict, blank=True)  # Armazena as binds personalizadas

    def get_preferences(self, padrao):
        return self.preferences.get(padrao, {})

    def set_preferences(self, padrao, binds):
        self.preferences[padrao] = binds
        self.save()

    def __str__(self):
        return f"{self.username} ({self.setor})"


class PadraoContagem(models.Model):
    pattern_type = models.CharField(
        max_length=100,
        verbose_name="Tipo do Padrão",
        default="padrao_perplan",
    )
    veiculo = models.CharField("Veículo", max_length=100)
    bind = models.CharField("Bind", max_length=50)

    def __str__(self):
        return f"{self.veiculo} ({self.bind}) - {self.pattern_type}"

class UserPadraoContagem(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,  
        related_name="binds_user"
    )
    pattern_type = models.CharField(max_length=100, default="padrao_perplan")
    veiculo = models.CharField("Veículo", max_length=100)
    bind = models.CharField("Bind", max_length=50)

    class Meta:
        unique_together = ("user", "pattern_type", "veiculo")

    def __str__(self):
        return f"{self.user.username} => {self.veiculo} ({self.bind}) - {self.pattern_type}"