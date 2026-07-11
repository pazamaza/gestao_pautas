from django import forms
from .models import Frequencia


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