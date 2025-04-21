# autenticao/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    name = forms.CharField(max_length=255, required=True)
    last_name = forms.CharField(max_length=255, required=True)
    email = forms.EmailField(required=True)
    setor = forms.ChoiceField(choices=[
        ('CON', 'Contagem'),
        ('DIG', 'Digitação'),
        ('P&D', 'Perci'),
        ('SUPER', 'Supervisão'),
    ], required=True)

    class Meta:
        model = User
        fields = ('username', 'name', 'last_name', 'email', 'setor', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Este e-mail já está em uso.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.name = self.cleaned_data['name']
        user.last_name = self.cleaned_data['last_name']
        user.setor = self.cleaned_data['setor']
        if commit:
            user.save()
        return user
