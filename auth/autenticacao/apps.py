# auth/autenticacao/apps.py
from django.apps import AppConfig


class AutenticacaoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'autenticacao'
    verbose_name = "Gestão de Usuários Padrões."

