from django import forms
from .models import Disciplina


class DisciplinaForm(forms.ModelForm):

    class Meta:

        model = Disciplina

        fields = '__all__'

        widgets = {

            'nome': forms.TextInput(
                attrs={
                    'class': 'form-control'
                }
            ),

            'sigla': forms.TextInput(
                attrs={
                    'class': 'form-control'
                }
            ),

            'descricao': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3
                }
            ),

            'ativa': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input'
                }
            )
        }