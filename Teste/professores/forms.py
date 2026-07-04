from django import forms
from .models import (Professor, AtribuicaoDocente)
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