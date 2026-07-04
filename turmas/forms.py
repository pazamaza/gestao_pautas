from django import forms
from .models import (AnoLetivo, PeriodoAcademico,
    Classe, Turma)


class AnoLetivoForm(forms.ModelForm):
    class Meta:
        model = AnoLetivo
        fields = '__all__'

class PeriodoAcademicoForm(forms.ModelForm):
    class Meta:
        model = PeriodoAcademico
        fields = '__all__'
        widgets = {
            'nome': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'ano_letivo': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'aberto': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'data_inicio_lancamento': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'data_fim_lancamento': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}
            ),
        }

class ClasseForm(forms.ModelForm):
    class Meta:
        model = Classe
        fields = '__all__'


class TurmaForm(forms.ModelForm):
    class Meta:
        model = Turma
        fields = '__all__'
        widgets = {
            'nome': forms.TextInput(
                attrs={
                    'class': 'form-control'
                }
            ),
            'classe': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            ),

            'ano_letivo': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            ),
        }