from django.db import models
from django.conf import settings

class PadraoContagem(models.Model):
    pattern_type = models.CharField(
        max_length=100,
        verbose_name="Tipo do Padrão",
        default="padrao_perplan",
    )
    veiculo = models.CharField("Veículo", max_length=100)
    bind = models.CharField("Bind", max_length=50)
    order = models.PositiveIntegerField("Ordem", default=0)

    class Meta: 
        verbose_name = "Padrão de Contagem"
        verbose_name_plural = "Padrões de Contagem"
        ordering = ['pattern_type', 'order', 'id']

    def __str__(self):
        return self.pattern_type

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
        verbose_name = "Usuário Padrão de Contagem"
        verbose_name_plural = "Usuários Padrão de Contagem"

    def __str__(self):
        return self.veiculo