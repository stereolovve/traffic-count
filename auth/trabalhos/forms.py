from django import forms

class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class PontoDetailForm(forms.Form):
    movimento = forms.CharField(
        label="Descrição",
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500'
        })
    )
    imagens = forms.FileField(
        label="Imagens (múltiplas)",
        widget=MultiFileInput(attrs={
            'multiple': True,
            'class': 'mt-1 block w-full text-gray-600'
        }),
        required=False
    )
    observacao = forms.CharField(
        label="Observação",
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500'
        }),
        required=False
    )
