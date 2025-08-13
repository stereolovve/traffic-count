# autenticacao/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'setor', 'is_active')
    search_fields = ('username', 'first_name','last_name', 'email', 'setor')
    list_filter = ('setor', 'is_active', 'is_staff')
    list_per_page = 25
    
    # Adiciona o campo setor aos fieldsets
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informações Adicionais', {'fields': ('setor',)}),
    )



