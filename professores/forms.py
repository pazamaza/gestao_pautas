from django import forms
from .models import (Professor, AtribuicaoDocente, DiretorTurma)
from django.contrib.auth.models import User


class ProfessorForm(forms.ModelForm):
    class Meta:
        model = Professor
        fields = '__all__'

class ProfessorUpdateForm(forms.ModelForm):
    class Meta:
        model = Professor
        fields = '__all__'

class AtribuicaoDocenteForm(forms.ModelForm):
    class Meta:
        model = AtribuicaoDocente
        fields = '__all__'
        widgets = {
            'professor': forms.Select(
                attrs={'class': 'form-select'} ),
            'disciplina': forms.Select(
                attrs={'class': 'form-select'}),
            'turma': forms.Select(
                attrs={'class': 'form-select'} ),
            'ano_letivo': forms.Select(
                attrs={'class': 'form-select'} ),
        }


class DiretorTurmaForm(forms.ModelForm):
    class Meta:
        model = DiretorTurma
        fields = '__all__'
        widgets = {
            'professor': forms.Select(
                attrs={'class': 'form-select'}),
            'turma': forms.Select(
                attrs={'class': 'form-select'}),
            'ano_letivo': forms.Select(
                attrs={'class': 'form-select'}),
            'ativo': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}),
        }


class ProfessorCompletoForm(forms.Form):

    first_name = forms.CharField(
        label='Nome',
        max_length=100
    )

    last_name = forms.CharField(
        label='Apelido',
        max_length=100,
        required=False
    )

    email = forms.EmailField(
        required=False
    )

    telefone = forms.CharField(
        max_length=20,
        required=False
    )

    numero_funcionario = forms.CharField(
        max_length=30
    )

    ativo = forms.BooleanField(
        required=False
    )




class ProfessorCadastroForm(forms.Form):

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

    numero_funcionario = forms.CharField(
    label='Nº Funcionário',
    widget=forms.TextInput(
        attrs={'class': 'form-control'}
    )
)

    telefone = forms.CharField(
    required=False,
    widget=forms.TextInput(
        attrs={'class': 'form-control'}
    )
)
    def clean_numero_funcionario(self):
        numero = self.cleaned_data['numero_funcionario'    ]
        if Professor.objects.filter(
        numero_funcionario=numero
    ).exists():
            raise forms.ValidationError(
            'Já existe um professor com este número.'
        )
        return numero
    
    def clean_username(self):
        username = self.cleaned_data[
        'username'
    ]
        if User.objects.filter(
        username=username
    ).exists():
            raise forms.ValidationError(
            'Este utilizador já existe.'
        )
        return username

class ProfessorEdicaoForm(forms.Form):
    first_name = forms.CharField(
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    last_name = forms.CharField(
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

    numero_funcionario = forms.CharField(
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    telefone = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    ativo = forms.BooleanField(
        required=False
    )