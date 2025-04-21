from django import forms
from .models import Croquis
from trabalhos.models import Codigo, Ponto
from padroes.models import PadraoContagem
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class CroquisForm(forms.ModelForm):
    codigo = forms.ModelChoiceField(
        queryset=Codigo.objects.all().order_by('cliente__nome', 'codigo'),
        empty_label="Selecione um código",
        widget=forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'})
    )
    ponto = forms.ModelChoiceField(
        queryset=Ponto.objects.all().order_by('codigo__cliente__nome', 'codigo__codigo', 'nome'),
        empty_label="Selecione um ponto",
        widget=forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'})
    )
    padrao = forms.ModelChoiceField(
        queryset=PadraoContagem.objects.distinct('pattern_type').order_by('pattern_type'),
        empty_label="Selecione um padrão",
        widget=forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'})
    )

    class Meta:
        model = Croquis
        fields = ['codigo', 'lote', 'ponto', 'movimento', 'padrao', 'data_croqui', 'imagem', 'status']
        widgets = {
            'data_croqui': forms.DateInput(attrs={'type': 'date', 'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'lote': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
            'imagem': forms.ClearableFileInput(attrs={'class': 'sr-only'}),
            'movimento': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define o valor padrão do status como 'P' (Pendente)
        self.fields['status'].required = False  # Torna o campo não obrigatório no formulário
        self.initial['status'] = 'P'  # Define o valor inicial
        self.fields['status'].widget = forms.HiddenInput()
        
        if self.instance.pk:
            self.fields['ponto'].queryset = (
                Ponto.objects.filter(codigo=self.instance.codigo)
                             .order_by('nome')
            )

        # 2. se for criação e o usuário já mudou o campo "codigo" (POST ou GET)
        if 'codigo' in self.data:
            try:
                codigo_id = int(self.data.get('codigo'))
                self.fields['ponto'].queryset = (
                    Ponto.objects.filter(codigo_id=codigo_id)
                                 .order_by('nome')
                )
            except (ValueError, TypeError):
                pass  # mantém vazio se o valor não for inteiro
        else:
            # formulário novo ‑‑ deixa a lista de pontos vazia
            self.fields['ponto'].queryset = Ponto.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance.pk:  # Se for uma criação nova
            cleaned_data['status'] = 'P'
        return cleaned_data

class CroquisFilterForm(forms.Form):
    codigo = forms.ModelChoiceField(
        queryset=Codigo.objects.all().order_by('cliente__nome', 'codigo'),
        empty_label="Todos os códigos",
        required=False,
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'hx-get': '/croquis/ajax/load-pontos/',
            'hx-target': '#div_id_ponto',
            'hx-trigger': 'change'
        })
    )
    ponto = forms.ModelChoiceField(
        queryset=Ponto.objects.none(),
        empty_label="Todos os pontos",
        required=False,
        widget=forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'})
    )
    lote = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'placeholder': 'Filtrar por lote...'
        })
    )
    status = forms.ChoiceField(
        choices=[('', 'Todos os status')] + Croquis.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'})
    )
    data_croqui = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
        })
    )
    created_by = forms.ModelChoiceField(
        queryset=User.objects.filter(croquis_criados__isnull=False).distinct().order_by('username'),
        empty_label="Todos os usuários",
        required=False,
        widget=forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'codigo' in self.data:
            try:
                codigo_id = int(self.data.get('codigo'))
                self.fields['ponto'].queryset = Ponto.objects.filter(
                    codigo_id=codigo_id
                ).order_by('nome')
            except (ValueError, TypeError):
                pass  # mantém o queryset vazio se o valor não for válido

class CroquisReviewForm(forms.ModelForm):
    observacao = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'rows': 4,
            'placeholder': 'Digite suas observações sobre o croqui...'
        })
    )

    class Meta:
        model = Croquis
        fields = ['status', 'observacao']
        widgets = {
            'status': forms.Select(
                attrs={
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
                },
                choices=[('A', 'Aprovado'), ('R', 'Reprovado')]  # Apenas opções de aprovação/reprovação
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Garante que apenas as opções de Aprovado/Reprovado estejam disponíveis
        self.fields['status'].choices = [('A', 'Aprovado'), ('R', 'Reprovado')]
