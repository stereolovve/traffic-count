# padroes/validators.py
from .models import PadraoContagem, UserPadraoContagem

class PadraoValidator:
    """Validador para dados de PadraoContagem"""
    
    @staticmethod
    def validate_data(data, padrao_id=None):
        """
        Valida dados de padrão de contagem
        padrao_id: para validação de update (excluir padrão atual)
        """
        errors = {}
        
        # Validar pattern_type
        pattern_type = data.get('pattern_type', '').strip()
        if not pattern_type:
            errors['pattern_type'] = 'Tipo do padrão é obrigatório.'
        elif len(pattern_type) > 100:
            errors['pattern_type'] = 'Tipo do padrão deve ter no máximo 100 caracteres.'
            
        # Validar veiculo
        veiculo = data.get('veiculo', '').strip()
        if not veiculo:
            errors['veiculo'] = 'Veículo é obrigatório.'
        elif len(veiculo) > 100:
            errors['veiculo'] = 'Veículo deve ter no máximo 100 caracteres.'
            
        # Validar bind
        bind = data.get('bind', '').strip()
        if not bind:
            errors['bind'] = 'Bind é obrigatório.'
        elif len(bind) > 50:
            errors['bind'] = 'Bind deve ter no máximo 50 caracteres.'
            
        # Validar order (se fornecido)
        order = data.get('order')
        if order is not None:
            try:
                order_int = int(order)
                if order_int < 0:
                    errors['order'] = 'Ordem deve ser um número positivo.'
            except (ValueError, TypeError):
                errors['order'] = 'Ordem deve ser um número válido.'
                
        # Verificar duplicata (pattern_type + veiculo + bind)
        if pattern_type and veiculo and bind:
            query = PadraoContagem.objects.filter(
                pattern_type=pattern_type,
                veiculo=veiculo,
                bind=bind
            )
            if padrao_id:
                query = query.exclude(pk=padrao_id)
            if query.exists():
                errors['duplicata'] = f'Já existe um padrão com tipo "{pattern_type}", veículo "{veiculo}" e bind "{bind}".'
                
        return errors

    @staticmethod
    def validate_multiple_data(pattern_type, veiculos, binds):
        """
        Valida dados para criação múltipla de padrões
        """
        errors = {}
        
        if not pattern_type or not pattern_type.strip():
            errors['pattern_type'] = 'Tipo do padrão é obrigatório.'
            
        if not veiculos or len(veiculos) == 0:
            errors['veiculos'] = 'Pelo menos um veículo é obrigatório.'
            
        if not binds or len(binds) == 0:
            errors['binds'] = 'Pelo menos um bind é obrigatório.'
            
        if len(veiculos) != len(binds):
            errors['mismatch'] = 'Número de veículos deve ser igual ao número de binds.'
            
        # Validar cada par veiculo/bind
        invalid_pairs = []
        duplicate_pairs = []
        
        for i, (veiculo, bind) in enumerate(zip(veiculos, binds)):
            if not veiculo or not veiculo.strip():
                invalid_pairs.append(f'Posição {i+1}: Veículo vazio')
            elif len(veiculo.strip()) > 100:
                invalid_pairs.append(f'Posição {i+1}: Veículo muito longo')
                
            if not bind or not bind.strip():
                invalid_pairs.append(f'Posição {i+1}: Bind vazio')
            elif len(bind.strip()) > 50:
                invalid_pairs.append(f'Posição {i+1}: Bind muito longo')
                
            # Verificar duplicata no banco
            if pattern_type and veiculo and bind:
                if PadraoContagem.objects.filter(
                    pattern_type=pattern_type.strip(),
                    veiculo=veiculo.strip(),
                    bind=bind.strip()
                ).exists():
                    duplicate_pairs.append(f'Veículo "{veiculo}" com bind "{bind}"')
                    
        if invalid_pairs:
            errors['invalid_pairs'] = invalid_pairs
            
        if duplicate_pairs:
            errors['duplicate_pairs'] = duplicate_pairs
            
        return errors

class UserPadraoValidator:
    """Validador para dados de UserPadraoContagem"""
    
    @staticmethod
    def validate_data(data, user, user_padrao_id=None):
        """
        Valida dados de padrão de usuário
        """
        errors = {}
        
        # Validar pattern_type
        pattern_type = data.get('pattern_type', '').strip()
        if not pattern_type:
            errors['pattern_type'] = 'Tipo do padrão é obrigatório.'
        elif len(pattern_type) > 100:
            errors['pattern_type'] = 'Tipo do padrão deve ter no máximo 100 caracteres.'
            
        # Validar veiculo
        veiculo = data.get('veiculo', '').strip()
        if not veiculo:
            errors['veiculo'] = 'Veículo é obrigatório.'
        elif len(veiculo) > 100:
            errors['veiculo'] = 'Veículo deve ter no máximo 100 caracteres.'
            
        # Validar bind
        bind = data.get('bind', '').strip()
        if not bind:
            errors['bind'] = 'Bind é obrigatório.'
        elif len(bind) > 50:
            errors['bind'] = 'Bind deve ter no máximo 50 caracteres.'
            
        # Verificar unique_together (user + pattern_type + veiculo)
        if user and pattern_type and veiculo:
            query = UserPadraoContagem.objects.filter(
                user=user,
                pattern_type=pattern_type,
                veiculo=veiculo
            )
            if user_padrao_id:
                query = query.exclude(pk=user_padrao_id)
            if query.exists():
                errors['duplicata'] = f'Você já possui um bind para o veículo "{veiculo}" no padrão "{pattern_type}".'
                
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
            if isinstance(error, list):
                messages.extend(error)
            else:
                messages.append(error)
        return messages