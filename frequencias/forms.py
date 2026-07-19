from django import forms
from .models import Frequencia, JustificacaoFalta


class RegistoFrequenciaForm(forms.Form):
    aluno_id = forms.IntegerField(widget=forms.HiddenInput())
    estado = forms.ChoiceField(
        choices=[
            (Frequencia.PRESENTE, 'Presença'),
            (Frequencia.FALTA, 'Ausência'),
            (Frequencia.JUSTIFICADA, 'Justificada'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial=Frequencia.PRESENTE,
    )


RegistoFrequenciaFormSet = forms.formset_factory(RegistoFrequenciaForm, extra=0)


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


class JustificacaoFaltaForm(forms.ModelForm):
    class Meta:
        model = JustificacaoFalta
        fields = ['motivo', 'documento']
        widgets = {
            'motivo': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4,
                    'placeholder': 'Descreva o motivo da falta'}),
            'documento': forms.ClearableFileInput(
                attrs={'class': 'form-control'}),
        }