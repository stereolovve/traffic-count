# folha_ponto/models.py
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from datetime import datetime, timedelta

class UserProfile(models.Model):
    """Perfil estendido do usuário para folha de ponto"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='folha_ponto_profile'
    )
    valor_hora = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Valor por Hora"
    )
    cargo = models.CharField(
        max_length=20,
        choices=[
            ('funcionario', 'Funcionário'),
            ('supervisor', 'Supervisor'),
        ],
        default='funcionario',
        verbose_name="Cargo"
    )
    departamento = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name="Departamento"
    )
    telefone = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name="Telefone"
    )
    data_admissao = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Data de Admissão"
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil de Usuário"
        verbose_name_plural = "Perfis de Usuários"

    def __str__(self):
        return f"{self.user.username} - {self.get_cargo_display()}"

    @property
    def is_supervisor(self):
        """Verifica se o usuário é supervisor baseado no cargo ou setor"""
        return self.cargo == 'supervisor' or self.user.setor == 'SUPER'

class WorkCode(models.Model):
    """Códigos de trabalho/projeto para registros de ponto"""
    codigo = models.CharField(
        max_length=20, 
        unique=True,
        verbose_name="Código"
    )
    descricao = models.CharField(
        max_length=200,
        verbose_name="Descrição"
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo"
    )
    # Relacionar com códigos do sistema de trabalhos se existir
    codigo_trabalho = models.ForeignKey(
        'trabalhos.Codigo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_codes',
        verbose_name="Código do Trabalho"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Código de Trabalho"
        verbose_name_plural = "Códigos de Trabalho"
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.descricao}"

class TimeRecord(models.Model):
    """Registro de ponto dos usuários"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='time_records',
        verbose_name="Usuário"
    )
    data = models.DateField(verbose_name="Data")
    
    # Período 1 (obrigatório)
    entrada1 = models.TimeField(verbose_name="Entrada 1")
    saida1 = models.TimeField(verbose_name="Saída 1")
    
    # Período 2 (opcional)
    entrada2 = models.TimeField(
        null=True, 
        blank=True,
        verbose_name="Entrada 2"
    )
    saida2 = models.TimeField(
        null=True, 
        blank=True,
        verbose_name="Saída 2"
    )
    
    # Período 3 (opcional)
    entrada3 = models.TimeField(
        null=True, 
        blank=True,
        verbose_name="Entrada 3"
    )
    saida3 = models.TimeField(
        null=True, 
        blank=True,
        verbose_name="Saída 3"
    )
    
    work_code = models.ForeignKey(
        WorkCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Código de Trabalho"
    )
    observacoes = models.TextField(
        blank=True,
        verbose_name="Observações"
    )
    
    # Status de aprovação
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pendente',
        verbose_name="Status"
    )
    
    # Quem aprovou/rejeitou
    aprovado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='aprovacoes_time_records',
        verbose_name="Aprovado por"
    )
    data_aprovacao = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data de Aprovação"
    )
    
    # Relacionar com sessões de contagem se existir
    sessao_contagem = models.ForeignKey(
        'contagens.Session',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='time_records',
        verbose_name="Sessão de Contagem"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Registro de Ponto"
        verbose_name_plural = "Registros de Ponto"
        unique_together = ('user', 'data')
        ordering = ['-data', 'user__username']
        indexes = [
            models.Index(fields=['user', 'data']),
            models.Index(fields=['data']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.data}"

    @property
    def horas_trabalhadas(self):
        """Calcula total de horas trabalhadas no dia"""
        total_seconds = 0
        
        # Período 1 (obrigatório)
        if self.entrada1 and self.saida1:
            entrada1 = datetime.combine(self.data, self.entrada1)
            saida1 = datetime.combine(self.data, self.saida1)
            if saida1 > entrada1:
                total_seconds += (saida1 - entrada1).total_seconds()
        
        # Período 2 (opcional)
        if self.entrada2 and self.saida2:
            entrada2 = datetime.combine(self.data, self.entrada2)
            saida2 = datetime.combine(self.data, self.saida2)
            if saida2 > entrada2:
                total_seconds += (saida2 - entrada2).total_seconds()
        
        # Período 3 (opcional)
        if self.entrada3 and self.saida3:
            entrada3 = datetime.combine(self.data, self.entrada3)
            saida3 = datetime.combine(self.data, self.saida3)
            if saida3 > entrada3:
                total_seconds += (saida3 - entrada3).total_seconds()
        
        return round(total_seconds / 3600, 2)  # Converter para horas

    @property
    def horas_formatadas(self):
        """Retorna horas trabalhadas formatadas (ex: 8h 30min)"""
        horas = self.horas_trabalhadas
        horas_int = int(horas)
        minutos = int((horas - horas_int) * 60)
        return f"{horas_int}h {minutos:02d}min"

    @property
    def valor_dia(self):
        """Calcula o valor a receber no dia"""
        try:
            profile = self.user.folha_ponto_profile
            return Decimal(str(self.horas_trabalhadas)) * profile.valor_hora
        except UserProfile.DoesNotExist:
            return Decimal('0.00')

    def clean(self):
        """Validações customizadas"""
        from django.core.exceptions import ValidationError
        
        # Validar que saída é maior que entrada em cada período
        if self.entrada1 and self.saida1 and self.saida1 <= self.entrada1:
            raise ValidationError("Saída 1 deve ser maior que Entrada 1")
        
        if self.entrada2 and self.saida2 and self.saida2 <= self.entrada2:
            raise ValidationError("Saída 2 deve ser maior que Entrada 2")
        
        if self.entrada3 and self.saida3 and self.saida3 <= self.entrada3:
            raise ValidationError("Saída 3 deve ser maior que Entrada 3")
        
        # Validar que períodos não se sobrepõem
        periodos = []
        if self.entrada1 and self.saida1:
            periodos.append((self.entrada1, self.saida1))
        if self.entrada2 and self.saida2:
            periodos.append((self.entrada2, self.saida2))
        if self.entrada3 and self.saida3:
            periodos.append((self.entrada3, self.saida3))
        
        for i, (inicio1, fim1) in enumerate(periodos):
            for j, (inicio2, fim2) in enumerate(periodos[i+1:], i+1):
                if not (fim1 <= inicio2 or fim2 <= inicio1):
                    raise ValidationError(f"Período {i+1} se sobrepõe com período {j+1}")

class Salary(models.Model):
    """Histórico de salários calculados"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='salaries',
        verbose_name="Usuário"
    )
    ano = models.IntegerField(verbose_name="Ano")
    mes = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name="Mês"
    )
    horas_trabalhadas = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Horas Trabalhadas"
    )
    valor_hora = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Valor/Hora no Período"
    )
    total_bruto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Total Bruto"
    )
    registros_aprovados = models.IntegerField(
        default=0,
        verbose_name="Registros Aprovados"
    )
    registros_pendentes = models.IntegerField(
        default=0,
        verbose_name="Registros Pendentes"
    )
    data_calculo = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Salário"
        verbose_name_plural = "Salários"
        unique_together = ('user', 'ano', 'mes')
        ordering = ['-ano', '-mes', 'user__username']

    def __str__(self):
        meses = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        return f"{self.user.username} - {meses[self.mes-1]}/{self.ano}"