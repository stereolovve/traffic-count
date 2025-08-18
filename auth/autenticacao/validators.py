# autenticacao/validators.py
import re
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

User = get_user_model()

class UserValidator:
    """Validador para dados de usuário"""
    
    SETOR_CHOICES = [
        ('CON', 'Contagem'),
        ('DIG', 'Digitação'),
        ('P&D', 'Perci'),
        ('SUPER', 'Supervisão'),
    ]
    
    @staticmethod
    def validate_data(data, user_id=None):
        """
        Valida dados de usuário
        user_id: para validação de update (excluir usuário atual)
        """
        errors = {}
        
        # Validar username
        username = data.get('username', '').strip()
        if not username:
            errors['username'] = 'Username é obrigatório.'
        elif not re.match(r'^[a-zA-Z]+\.[a-zA-Z]+$', username):
            errors['username'] = 'O username deve estar no formato nome.sobrenome.'
        else:
            # Verificar duplicata
            query = User.objects.filter(username=username)
            if user_id:
                query = query.exclude(pk=user_id)
            if query.exists():
                errors['username'] = 'Este username já está em uso.'
        
        # Validar name
        name = data.get('name', '').strip()
        if not name:
            errors['name'] = 'Nome é obrigatório.'
        elif len(name) > 255:
            errors['name'] = 'Nome deve ter no máximo 255 caracteres.'
            
        # Validar last_name
        last_name = data.get('last_name', '').strip()
        if not last_name:
            errors['last_name'] = 'Sobrenome é obrigatório.'
        elif len(last_name) > 255:
            errors['last_name'] = 'Sobrenome deve ter no máximo 255 caracteres.'
            
        # Validar email
        email = data.get('email', '').strip()
        if not email:
            errors['email'] = 'E-mail é obrigatório.'
        else:
            # Verificar duplicata
            query = User.objects.filter(email=email)
            if user_id:
                query = query.exclude(pk=user_id)
            if query.exists():
                errors['email'] = 'Este e-mail já está em uso.'
                
        # Validar setor
        setor = data.get('setor', '')
        valid_setores = [choice[0] for choice in UserValidator.SETOR_CHOICES]
        if not setor:
            errors['setor'] = 'Setor é obrigatório.'
        elif setor not in valid_setores:
            errors['setor'] = f'Setor inválido. Escolha entre: {", ".join(valid_setores)}'
            
        # Validar senhas (se fornecidas)
        password1 = data.get('password1', '')
        password2 = data.get('password2', '')
        
        if password1 or password2:  # Se pelo menos uma senha foi fornecida
            if not password1:
                errors['password1'] = 'Senha é obrigatória.'
            elif len(password1) < 8:
                errors['password1'] = 'Senha deve ter pelo menos 8 caracteres.'
            else:
                try:
                    validate_password(password1)
                except DjangoValidationError as e:
                    errors['password1'] = '; '.join(e.messages)
                    
            if not password2:
                errors['password2'] = 'Confirmação de senha é obrigatória.'
            elif password1 != password2:
                errors['password2'] = 'As senhas não coincidem.'
                
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