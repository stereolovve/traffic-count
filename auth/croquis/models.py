#croquis/models.py
from django.db import models
from django.conf import settings
from trabalhos.models import Cliente, Ponto, Codigo
from padroes.models import PadraoContagem


class Croquis(models.Model):
    """
    Represents a Croqui, which is a graphical representation or sketch associated with a given 'Codigo' and 'Ponto'.
    This model tracks various attributes such as status, date, time, and associated images. It also keeps information
    about its creation and approval.

    Attributes:
        STATUS_CHOICES (list): The possible status values for a Croqui.
        codigo (ForeignKey): A reference to the 'Codigo' model.
        lote (CharField): The batch or lot associated with the Croqui.
        ponto (ForeignKey): A reference to the 'Ponto' model.
        movimento (CharField): The movement associated with the Croqui.
        padrao (ForeignKey): A reference to the 'PadraoContagem' model.
        data_croqui (DateField): The date of the Croqui.
        hora_inicio (TimeField): The start time of the Croqui.
        hora_fim (TimeField): The end time of the Croqui.
        imagem (ImageField): The image associated with the Croqui.
        status (CharField): The status of the Croqui.
        observacao (TextField): Observations or notes about the Croqui.
        created_by (ForeignKey): The user who created the Croqui.
        created_at (DateTimeField): The timestamp of when the Croqui was created.
        aprovado_por (ForeignKey): The user who approved the Croqui.
        aprovado_em (DateTimeField): The timestamp of when the Croqui was approved.
    """

    STATUS_CHOICES = [
        ('P', 'Pendente'),
        ('A', 'Aprovado'),
        ('R', 'Reprovado'),
    ]

    codigo = models.ForeignKey(
        Codigo, 
        on_delete=models.CASCADE, 
        related_name='croquis',
        db_column='codigo'
    )
    lote = models.CharField(max_length=100)
    ponto = models.ForeignKey(
        Ponto, 
        on_delete=models.CASCADE, 
        related_name='croquis',
        db_column='ponto'
    )
    movimento = models.CharField(max_length=100)
    padrao = models.ForeignKey(
        PadraoContagem, 
        on_delete=models.CASCADE, 
        related_name='croquis',
        db_column='padrao'
    )
    data_croqui = models.DateField()
    hora_inicio = models.TimeField(null=True)  
    hora_fim = models.TimeField(null=True)  
    imagem = models.ImageField(upload_to='croquis/')
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='P')
    observacao = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='croquis_criados'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    aprovado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='croquis_aprovados',
        null=True,
        blank=True
    )
    aprovado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Croqui'
        verbose_name_plural = 'Croquis'
        ordering = ['-created_at']
        db_table = 'croquis'  

    def __str__(self):
        return f"{self.codigo} - {self.ponto} ({self.data_croqui})"
