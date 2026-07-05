from django import forms
from .models import Nota
from .models import Avaliacao
from .models import ResultadoDisciplina


class ObservacoesValidacaoForm(forms.Form):
    observacoes_validacao = forms.CharField(
        label='Observações',
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'rows': 4}
        )
    )


class ImportarNotasExcelForm(forms.Form):
    arquivo = forms.FileField(
        label='Arquivo Excel',
        help_text='Use o modelo da pauta e preencha as colunas MAC, NPP e NPT.',
        widget=forms.ClearableFileInput(
            attrs={
                'class': 'form-control',
                'accept': '.xlsx',
            }
        )
    )

class AvaliacaoForm(forms.ModelForm):
    class Meta:
        model = Avaliacao
        fields = ['atribuicao', 'periodo']
        widgets = {'atribuicao': forms.Select(
                attrs={'class': 'form-select'} ),

            'periodo': forms.Select(attrs={'class': 'form-select'}
            ),   }

class NotaForm(forms.ModelForm):
    class Meta:
        model = Nota
        fields = '__all__'
        widgets = {
            'avaliacao': forms.Select(
                attrs={'class': 'form-select'}
            ),

            'aluno': forms.Select(
                attrs={'class': 'form-select'}
            ),

            'mac': forms.NumberInput(
                attrs={'class': 'form-control'}
            ),

            'npp': forms.NumberInput(
                attrs={'class': 'form-control'}
            ),

            'npt': forms.NumberInput(
                attrs={'class': 'form-control'}
            ),

            'observacao': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        avaliacao = cleaned_data.get('avaliacao')

        if avaliacao and not avaliacao.periodo.periodo_lancamento_ativo():
            raise forms.ValidationError(
                'Fora do período de lançamento de notas para este trimestre.'
            )

        return cleaned_data

class ResultadoDisciplinaForm(forms.ModelForm):

    class Meta:

        model = ResultadoDisciplina

        fields = [
            'aluno',
            'disciplina',
            'ano_letivo',
            'mt1',
            'mt2',
            'mt3',
            'exame',
            'nota_recurso'
        ]

        widgets = {

            'aluno': forms.Select(
                attrs={'class': 'form-select'}
            ),

            'disciplina': forms.Select(
                attrs={'class': 'form-select'}
            ),

            'ano_letivo': forms.Select(
                attrs={'class': 'form-select'}
            ),

            'mt1': forms.NumberInput(
                attrs={'class': 'form-control'}
            ),

            'mt2': forms.NumberInput(
                attrs={'class': 'form-control'}
            ),

            'mt3': forms.NumberInput(
                attrs={'class': 'form-control'}
            ),

            'exame': forms.NumberInput(
                attrs={'class': 'form-control'}
            ),

            'nota_recurso': forms.NumberInput(
                attrs={'class': 'form-control'}
            ),
        }
