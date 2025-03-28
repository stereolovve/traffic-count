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

    preferences = models.JSONField(default=dict, blank=True)

    def get_preferences(self, padrao):
        return self.preferences.get(padrao, {})

    def set_preferences(self, padrao, binds):
        self.preferences[padrao] = binds
        self.save()
    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
    def __str__(self):
        return f"{self.username} ({self.setor})"
