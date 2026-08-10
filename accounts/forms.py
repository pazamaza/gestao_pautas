from django import forms
from django.contrib.auth.models import User


class SubdiretorPedagogicoCadastroForm(forms.Form):

    first_name = forms.CharField(
        label='Nome',
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    last_name = forms.CharField(
        label='Apelido',
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    username = forms.CharField(
        label='Nome de Utilizador',
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={'class': 'form-control'}
        )
    )

    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(
            attrs={'class': 'form-control'}
        )
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                'Este utilizador já existe.'
            )
        return username


class SubdiretorPedagogicoEdicaoForm(forms.Form):

    first_name = forms.CharField(
        label='Nome',
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    last_name = forms.CharField(
        label='Apelido',
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={'class': 'form-control'}
        )
    )

    ativo = forms.BooleanField(
        label='Ativo',
        required=False
    )


class ContaAdministrativaCadastroForm(forms.Form):
    """Cadastro genérico de conta administrativa (Diretor Geral, Chefe de
    Secretaria, Coordenador de Turno, Coordenador de Pais/EE)."""

    first_name = forms.CharField(
        label='Nome',
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    last_name = forms.CharField(
        label='Apelido',
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    username = forms.CharField(
        label='Nome de Utilizador',
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={'class': 'form-control'}
        )
    )

    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(
            attrs={'class': 'form-control'}
        )
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                'Este utilizador já existe.'
            )
        return username


class ContaAdministrativaEdicaoForm(forms.Form):

    first_name = forms.CharField(
        label='Nome',
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    last_name = forms.CharField(
        label='Apelido',
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={'class': 'form-control'}
        )
    )

    ativo = forms.BooleanField(
        label='Ativo',
        required=False
    )
