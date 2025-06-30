from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import datetime, timedelta

class Ticket(models.Model):
    TURNO_CHOICES = [
        ('MANHA', 'Manhã'),
        ('NOITE', 'Noite'),
    ]
    
    STATUS_CHOICES = [
        ('AGUARDANDO', 'Aguardando'),
        ('INICIADO', 'Iniciado'),
        ('CONTANDO', 'Contando'),
        ('PAUSADO', 'Pausado'),
        ('FINALIZADO', 'Finalizado'),
    ]
    
    PRIORIDADE_CHOICES = [
        ('BAIXA', 'Baixa'),
        ('MEDIA', 'Média'),
        ('ALTA', 'Alta'),
        ('URGENTE', 'Urgente'),
    ]
    
    # Campos básicos
    turno = models.CharField(
        max_length=10,
        choices=TURNO_CHOICES,
        verbose_name="Turno"
    )
    
    coordenador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tickets_coordenados',
        verbose_name="Coordenador",
        limit_choices_to={'setor': 'SUPER'}
    )
    
    codigo = models.ForeignKey(
        'trabalhos.Codigo',
        on_delete=models.CASCADE,
        verbose_name="Código",
        help_text="Código do trabalho"
    )
    
    cam = models.CharField(
        max_length=100,
        verbose_name="CAM",
        help_text="Identificação da câmera"
    )
    
    mov = models.CharField(
        max_length=100,
        verbose_name="MOV",
        help_text="Identificação do movimento"
    )
    
    padrao = models.ForeignKey(
        'padroes.PadraoContagem',
        on_delete=models.CASCADE,
        verbose_name="Padrão",
        help_text="Padrão de contagem"
    )
    
    duracao = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Duração (horas)",
        help_text="Duração do vídeo em horas",
        validators=[MinValueValidator(0.01), MaxValueValidator(999.99)]
    )
    
    periodo_inicio = models.TimeField(
        verbose_name="Início do Período",
        help_text="Horário de início da contagem"
    )
    
    periodo_fim = models.TimeField(
        verbose_name="Fim do Período",
        help_text="Horário de fim da contagem"
    )
    
    data = models.DateField(
        verbose_name="Data",
        help_text="Data da contagem"
    )
    
    nivel = models.PositiveIntegerField(
        verbose_name="Nível",
        help_text="Nível de complexidade",
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    
    prioridade = models.CharField(
        max_length=10,
        choices=PRIORIDADE_CHOICES,
        default='MEDIA',
        verbose_name="Prioridade"
    )
    
    observacao = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observação",
        help_text="Observações adicionais"
    )
    
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='AGUARDANDO',
        verbose_name="Status"
    )
    
    pesquisador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_pesquisados',
        verbose_name="Pesquisador",
        help_text="Usuário responsável pela pesquisa"
    )
    
    data_atribuicao = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data de Atribuição",
        help_text="Data e hora em que o ticket foi atribuído"
    )
    
    data_finalizacao = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data de Finalização",
        help_text="Data e hora em que o ticket foi finalizado"
    )
    
    # Campos de auditoria
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )
    
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em"
    )
    
    class Meta:
        verbose_name = "Ticket"
        verbose_name_plural = "Tickets"
        ordering = ['-data', '-criado_em']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['data']),
            models.Index(fields=['coordenador']),
            models.Index(fields=['pesquisador']),
        ]
    
    def __str__(self):
        return f"Ticket {self.id} - {self.codigo.codigo} - {self.data}"
    
    def save(self, *args, **kwargs):
        # Atualizar data de atribuição quando pesquisador for definido
        if self.pesquisador and not self.data_atribuicao:
            self.data_atribuicao = timezone.now()
        
        # Atualizar data de finalização quando status for finalizado
        if self.status == 'FINALIZADO' and not self.data_finalizacao:
            self.data_finalizacao = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def periodo_formatado(self):
        """Retorna o período formatado"""
        return f"{self.periodo_inicio.strftime('%H:%M')} - {self.periodo_fim.strftime('%H:%M')}"
    
    @property
    def duracao_formatada(self):
        """Retorna a duração formatada"""
        horas = int(self.duracao)
        minutos = int((self.duracao - horas) * 60)
        return f"{horas}h {minutos}min"
    
    @property
    def horas_periodo(self):
        """Calcula as horas do período (intervalo de tempo)"""
        if self.periodo_inicio and self.periodo_fim:
            # Criar datetime objects para o mesmo dia
            inicio = datetime.combine(self.data, self.periodo_inicio)
            fim = datetime.combine(self.data, self.periodo_fim)
            
            # Se o fim for menor que o início, significa que passou da meia-noite
            if fim < inicio:
                fim += timedelta(days=1)
            
            # Calcular diferença
            diferenca = fim - inicio
            horas = diferenca.total_seconds() / 3600
            return round(horas, 2)
        return 0
    
    @property
    def horas_periodo_formatada(self):
        """Retorna as horas do período formatadas"""
        horas = self.horas_periodo
        horas_int = int(horas)
        minutos = int((horas - horas_int) * 60)
        return f"{horas_int}h {minutos:02d}min"
    
    def pode_ser_atribuido(self):
        """Verifica se o ticket pode ser atribuído"""
        return self.status in ['AGUARDANDO', 'PAUSADO']
    
    def pode_ser_iniciado(self):
        """Verifica se o ticket pode ser iniciado"""
        return self.status in ['AGUARDANDO', 'PAUSADO'] and self.pesquisador is not None
    
    def pode_ser_pausado(self):
        """Verifica se o ticket pode ser pausado"""
        return self.status in ['INICIADO', 'CONTANDO']
    
    def pode_ser_finalizado(self):
        """Verifica se o ticket pode ser finalizado"""
        return self.status in ['INICIADO', 'CONTANDO', 'PAUSADO'] 