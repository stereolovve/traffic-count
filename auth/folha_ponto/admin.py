# folha_ponto/admin.py
from django.contrib import admin
from .models import UserProfile, WorkCode, TimeRecord, Salary

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'cargo', 'valor_hora', 'departamento', 'ativo', 'created_at']
    list_filter = ['cargo', 'ativo', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'departamento']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Usuário', {
            'fields': ('user',)
        }),
        ('Informações Profissionais', {
            'fields': ('cargo', 'valor_hora', 'departamento', 'data_admissao')
        }),
        ('Contato', {
            'fields': ('telefone',)
        }),
        ('Status', {
            'fields': ('ativo',)
        }),
        ('Auditoria', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(WorkCode)
class WorkCodeAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'descricao', 'ativo', 'codigo_trabalho', 'created_at']
    list_filter = ['ativo', 'created_at']
    search_fields = ['codigo', 'descricao']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Código de Trabalho', {
            'fields': ('codigo', 'descricao', 'ativo')
        }),
        ('Integração', {
            'fields': ('codigo_trabalho',),
            'description': 'Vinculação com códigos do sistema de trabalhos'
        }),
        ('Auditoria', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(TimeRecord)
class TimeRecordAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'data', 'entrada1', 'saida1', 'horas_formatadas', 
        'work_code', 'status', 'aprovado_por'
    ]
    list_filter = ['status', 'data', 'work_code', 'aprovado_por']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at', 'horas_trabalhadas', 'valor_dia']
    date_hierarchy = 'data'
    
    fieldsets = (
        ('Usuário e Data', {
            'fields': ('user', 'data')
        }),
        ('Horários - Período 1', {
            'fields': ('entrada1', 'saida1')
        }),
        ('Horários - Período 2', {
            'fields': ('entrada2', 'saida2'),
            'classes': ('collapse',)
        }),
        ('Horários - Período 3', {
            'fields': ('entrada3', 'saida3'),
            'classes': ('collapse',)
        }),
        ('Informações Adicionais', {
            'fields': ('work_code', 'observacoes', 'sessao_contagem')
        }),
        ('Aprovação', {
            'fields': ('status', 'aprovado_por', 'data_aprovacao')
        }),
        ('Cálculos', {
            'fields': ('horas_trabalhadas', 'valor_dia'),
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        # Se está aprovando/rejeitando e não tem aprovado_por, definir como usuário atual
        if obj.status in ['aprovado', 'rejeitado'] and not obj.aprovado_por:
            obj.aprovado_por = request.user
            from django.utils import timezone
            obj.data_aprovacao = timezone.now()
        super().save_model(request, obj, form, change)

@admin.register(Salary)
class SalaryAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'mes_display', 'ano', 'horas_trabalhadas', 
        'valor_hora', 'total_bruto', 'registros_aprovados', 'data_calculo'
    ]
    list_filter = ['ano', 'mes', 'data_calculo']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['data_calculo']
    
    fieldsets = (
        ('Usuário e Período', {
            'fields': ('user', 'ano', 'mes')
        }),
        ('Cálculos', {
            'fields': ('horas_trabalhadas', 'valor_hora', 'total_bruto')
        }),
        ('Estatísticas', {
            'fields': ('registros_aprovados', 'registros_pendentes')
        }),
        ('Auditoria', {
            'fields': ('data_calculo',)
        })
    )
    
    def mes_display(self, obj):
        meses = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        return meses[obj.mes - 1]
    mes_display.short_description = 'Mês'