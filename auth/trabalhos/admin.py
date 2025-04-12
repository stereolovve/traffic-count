from django.contrib import admin
from .models import Cliente, Codigo, Ponto

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    search_fields = ['nome']

@admin.register(Codigo)
class CodigoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'cliente']
    list_filter = ['cliente']
    search_fields = ['codigo']

@admin.register(Ponto)
class PontoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'codigo', 'localizacao']
    list_filter = ['codigo__cliente', 'codigo']
    search_fields = ['nome']
