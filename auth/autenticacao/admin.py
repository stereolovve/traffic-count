# autenticacao/admin.py
from django.contrib import admin
from .models import User
from .models import PadraoContagem
from .models import UserPadraoContagem


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'setor', 'is_active')
    search_fields = ('username', 'first_name','last_name', 'email', 'setor')
    list_filter = ('setor', 'is_active', 'is_staff')
    list_per_page = 25

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