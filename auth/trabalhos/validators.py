# trabalhos/validators.py
from rest_framework import serializers
from .models import Cliente, Codigo, Ponto

class ClienteValidator:
    """Validador para dados de Cliente"""
    
    @staticmethod
    def validate_data(data):
        errors = {}
        
        nome = data.get('nome', '').strip()
        if not nome:
            errors['nome'] = 'Nome do cliente é obrigatório.'
        elif len(nome) > 100:
            errors['nome'] = 'Nome deve ter no máximo 100 caracteres.'
        elif Cliente.objects.filter(nome=nome).exists():
            errors['nome'] = 'Já existe um cliente com este nome.'
            
        return errors

class CodigoValidator:
    """Validador para dados de Código"""
    
    @staticmethod
    def validate_data(data):
        errors = {}
        
        codigo = data.get('codigo', '').strip()
        cliente_id = data.get('cliente_id')
        descricao = data.get('descricao', '').strip()
        
        if not codigo:
            errors['codigo'] = 'Código é obrigatório.'
        elif len(codigo) > 20:
            errors['codigo'] = 'Código deve ter no máximo 20 caracteres.'
            
        if not cliente_id:
            errors['cliente'] = 'Cliente é obrigatório.'
        else:
            try:
                cliente = Cliente.objects.get(id=cliente_id)
                # Verificar se já existe este código para o cliente
                if Codigo.objects.filter(cliente=cliente, codigo=codigo).exists():
                    errors['codigo'] = f'Já existe o código "{codigo}" para este cliente.'
            except Cliente.DoesNotExist:
                errors['cliente'] = 'Cliente não encontrado.'
        
        if descricao and len(descricao) > 200:
            errors['descricao'] = 'Descrição deve ter no máximo 200 caracteres.'
            
        return errors

class PontoValidator:
    """Validador para dados de Ponto"""
    
    @staticmethod
    def validate_data(data):
        errors = {}
        
        nome = data.get('nome', '').strip()
        codigo_id = data.get('codigo_id')
        localizacao = data.get('localizacao', '').strip()
        
        if not nome:
            errors['nome'] = 'Nome do ponto é obrigatório.'
        elif len(nome) > 100:
            errors['nome'] = 'Nome deve ter no máximo 100 caracteres.'
            
        if not codigo_id:
            errors['codigo'] = 'Código é obrigatório.'
        else:
            try:
                codigo = Codigo.objects.get(id=codigo_id)
                # Verificar se já existe este ponto para o código
                if Ponto.objects.filter(codigo=codigo, nome=nome).exists():
                    errors['nome'] = f'Já existe o ponto "{nome}" para este código.'
            except Codigo.DoesNotExist:
                errors['codigo'] = 'Código não encontrado.'
        
        if localizacao and len(localizacao) > 200:
            errors['localizacao'] = 'Localização deve ter no máximo 200 caracteres.'
            
        return errors

class ValidationResult:
    """Classe para encapsular resultado de validação"""
    
    def __init__(self, is_valid=True, errors=None, cleaned_data=None):
        self.is_valid = is_valid
        self.errors = errors or {}
        self.cleaned_data = cleaned_data or {}
    
    @property
    def has_errors(self):
        return bool(self.errors)
    
    def get_error_messages(self):
        """Retorna lista de mensagens de erro"""
        messages = []
        for field, error in self.errors.items():
            messages.append(error)
        return messages