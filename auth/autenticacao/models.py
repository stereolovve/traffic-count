from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.

class User(AbstractUser):
    nome_completo = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    setor_opcoes = [
        ('CON', 'Contagem'),
        ('DIG', 'Digitação'),
        ('P&D', 'Perci'),
        ('SUPER', 'Supervisao'),
    ]
    setor = models.CharField(
        max_length=5,
        choices=setor_opcoes,
        verbose_name='Setor',
        default='CON')
    
    def __str__(self):
        return self.username
