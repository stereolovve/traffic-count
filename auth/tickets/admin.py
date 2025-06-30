from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Ticket

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'codigo', 'turno', 'data', 'periodo_formatado', 
        'coordenador', 'pesquisador', 'status', 'prioridade', 'nivel'
    ]
    
    list_filter = [
        'status', 'prioridade', 'turno', 'data', 'coordenador', 
        'pesquisador', 'nivel', 'criado_em'
    ]
    
    search_fields = [
        'codigo__codigo', 'codigo__descricao', 'cam', 'mov', 
        'observacao', 'coordenador__username', 'pesquisador__username'
    ]
    
    list_editable = ['status', 'prioridade']
    
    readonly_fields = [
        'criado_em', 'atualizado_em', 'data_atribuicao', 'data_finalizacao',
        'periodo_formatado', 'duracao_formatada'
    ]
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('turno', 'data', 'periodo_inicio', 'periodo_fim', 'duracao')
        }),
        ('Identificação', {
            'fields': ('codigo', 'cam', 'mov', 'padrao')
        }),
        ('Classificação', {
            'fields': ('nivel', 'prioridade', 'observacao')
        }),
        ('Responsáveis', {
            'fields': ('coordenador', 'pesquisador')
        }),
        ('Status e Controle', {
            'fields': ('status', 'data_atribuicao', 'data_finalizacao')
        }),
        ('Auditoria', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )
    
    autocomplete_fields = ['coordenador', 'pesquisador', 'codigo', 'padrao']
    
    date_hierarchy = 'data'
    
    list_per_page = 25
    
    actions = ['marcar_como_aguardando', 'marcar_como_iniciado', 'marcar_como_finalizado']
    
    def periodo_formatado(self, obj):
        return obj.periodo_formatado
    periodo_formatado.short_description = 'Período'
    
    def duracao_formatada(self, obj):
        return obj.duracao_formatada
    duracao_formatada.short_description = 'Duração'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'coordenador', 'pesquisador', 'codigo', 'codigo__cliente', 'padrao'
        )
    
    def marcar_como_aguardando(self, request, queryset):
        updated = queryset.update(status='AGUARDANDO')
        self.message_user(request, f'{updated} tickets marcados como aguardando.')
    marcar_como_aguardando.short_description = "Marcar selecionados como aguardando"
    
    def marcar_como_iniciado(self, request, queryset):
        updated = queryset.update(status='INICIADO')
        self.message_user(request, f'{updated} tickets marcados como iniciado.')
    marcar_como_iniciado.short_description = "Marcar selecionados como iniciado"
    
    def marcar_como_finalizado(self, request, queryset):
        updated = queryset.update(status='FINALIZADO')
        self.message_user(request, f'{updated} tickets marcados como finalizado.')
    marcar_como_finalizado.short_description = "Marcar selecionados como finalizado"
    
    def save_model(self, request, obj, form, change):
        # Lógica adicional ao salvar
        if not change:  # Novo ticket
            if not obj.coordenador:
                obj.coordenador = request.user
        super().save_model(request, obj, form, change)
