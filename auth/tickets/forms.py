from django import forms
from django.contrib.auth import get_user_model
from .models import Ticket
from trabalhos.models import Codigo
from padroes.models import PadraoContagem

User = get_user_model()

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = [
            'turno', 'coordenador', 'codigo', 'cam', 'mov', 'padrao',
            'duracao', 'periodo_inicio', 'periodo_fim', 'data', 'nivel',
            'prioridade', 'observacao', 'status', 'pesquisador'
        ]
        widgets = {
            'turno': forms.Select(attrs={'class': 'form-control'}),
            'coordenador': forms.Select(attrs={'class': 'form-control'}),
            'codigo': forms.Select(attrs={'class': 'form-control'}),
            'cam': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Identificação da câmera'}),
            'mov': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Identificação do movimento'}),
            'padrao': forms.Select(attrs={'class': 'form-control'}),
            'duracao': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'periodo_inicio': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'periodo_fim': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'nivel': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '10'}),
            'prioridade': forms.Select(attrs={'class': 'form-control'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observações adicionais'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'pesquisador': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar coordenadores apenas com setor SUPER
        self.fields['coordenador'].queryset = User.objects.filter(setor='SUPER').order_by('username')
        
        # Ordenar códigos por código e mostrar código + descrição
        self.fields['codigo'].queryset = Codigo.objects.all().order_by('codigo')
        self.fields['codigo'].label_from_instance = lambda obj: f"{obj.codigo} - {obj.descricao}" if obj.descricao else obj.codigo
        
        # Ordenar padrões por pattern_type
        self.fields['padrao'].queryset = PadraoContagem.objects.all().order_by('pattern_type')
        
        # Ordenar pesquisadores por username
        self.fields['pesquisador'].queryset = User.objects.all().order_by('username')
        
        # Tornar pesquisador opcional
        self.fields['pesquisador'].required = False
        
        # Definir valores padrão
        if not self.instance.pk:
            self.fields['status'].initial = 'AGUARDANDO'
            self.fields['prioridade'].initial = 'MEDIA'
            self.fields['nivel'].initial = 5
    
    def clean(self):
        cleaned_data = super().clean()
        periodo_inicio = cleaned_data.get('periodo_inicio')
        periodo_fim = cleaned_data.get('periodo_fim')
        
        if periodo_inicio and periodo_fim:
            if periodo_inicio >= periodo_fim:
                raise forms.ValidationError(
                    'O horário de início deve ser anterior ao horário de fim.'
                )
        
        return cleaned_data
    
    def clean_duracao(self):
        duracao = self.cleaned_data.get('duracao')
        if duracao and duracao <= 0:
            raise forms.ValidationError('A duração deve ser maior que zero.')
        return duracao
    
    def clean_nivel(self):
        nivel = self.cleaned_data.get('nivel')
        if nivel and (nivel < 1 or nivel > 10):
            raise forms.ValidationError('O nível deve estar entre 1 e 10.')
        return nivel

class TicketFilterForm(forms.Form):
    """Formulário para filtrar tickets"""
    status = forms.ChoiceField(
        choices=[('', 'Todos')] + Ticket.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    prioridade = forms.ChoiceField(
        choices=[('', 'Todas')] + Ticket.PRIORIDADE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    turno = forms.ChoiceField(
        choices=[('', 'Todos')] + Ticket.TURNO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    data = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    coordenador = forms.ModelChoiceField(
        queryset=User.objects.filter(setor='SUPER').order_by('username'),
        required=False,
        empty_label="Todos os coordenadores",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    pesquisador = forms.ModelChoiceField(
        queryset=User.objects.all().order_by('username'),
        required=False,
        empty_label="Todos os pesquisadores",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por código, descrição, CAM, MOV...'
        })
    ) 