# autenticacao/admin.py
from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'nome_completo', 'email', 'setor', 'is_active')
    search_fields = ('username', 'nome_completo', 'email', 'setor')
    list_filter = ('setor', 'is_active', 'is_staff')
    