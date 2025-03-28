# auth/padroes/forms.py
from django import forms
from .models import PadraoContagem


class PadraoContagemForm(forms.ModelForm):
    class Meta:
        model = PadraoContagem
        fields = ['pattern_type', 'veiculo', 'bind']