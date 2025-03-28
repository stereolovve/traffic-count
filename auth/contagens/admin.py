from django.contrib import admin
from .models import Session, Counting

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('sessao', 'codigo', 'ponto', 'data', 'horario_inicio', 'ativa', 'movimentos')
    search_fields = ('sessao', 'codigo', 'ponto', 'data', 'horario_inicio')
    list_filter = ('ativa',)
    list_per_page = 25

