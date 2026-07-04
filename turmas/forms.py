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