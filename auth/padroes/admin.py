from django.contrib import admin
from .models import PadraoContagem, UserPadraoContagem

# Register your models here.
@admin.register(PadraoContagem)
class PadraoContagemAdmin(admin.ModelAdmin):
    list_display = ('pattern_type', 'veiculo', 'bind')
    search_fields = ('pattern_type', 'veiculo', 'bind')
    list_filter = ('pattern_type',)
    list_per_page = 25

@admin.register(UserPadraoContagem)
class UserPadraoContagemAdmin(admin.ModelAdmin):
    list_display = ('user', 'pattern_type', 'veiculo', 'bind')
    search_fields = ('user__username', 'pattern_type', 'veiculo')
    list_filter = ('pattern_type',)
    list_per_page = 25
