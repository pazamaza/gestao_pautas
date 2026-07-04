from django import forms
from .models import Aluno

class AlunoForm(forms.ModelForm):
    class Meta:
        model = Aluno
        fields = '__all__'
        widgets = {
            'nome': forms.TextInput(
                attrs={
                    'class': 'form-control'
                }
            ),
            'numero_processo': forms.TextInput(
                attrs={
                    'class': 'form-control'
                }
            ),
            'data_nascimento': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                }
            ),
            'sexo': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            ),
            'turma': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            ),
            'encarregado': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            ),
        }