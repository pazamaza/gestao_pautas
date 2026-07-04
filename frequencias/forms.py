from django import forms
from .models import Frequencia

class FrequenciaForm(forms.ModelForm):
    class Meta:
        model = Frequencia
        fields = '__all__'
        widgets = {
            'aluno': forms.Select(
                attrs={'class': 'form-select'  }  ),
            'atribuicao': forms.Select(
                attrs={'class': 'form-select' }  ),
            'data': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'
                } ),
            'estado': forms.Select(
                attrs={'class': 'form-select'} ),
            'observacao': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3 })
        }