from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
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
    
    def clean(self):
        # Validação do username no formato nome.sobrenome
        if not self.username or not self.username.count('.') == 1:
            raise ValidationError("O username deve estar no formato nome.sobrenome.")

    def save(self, *args, **kwargs):
        # Executa a validação antes de salvar
        self.clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Excluir logs associados antes de excluir o usuário
        LogEntry.objects.filter(user=self).delete()
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.username