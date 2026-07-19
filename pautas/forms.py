from django import forms
from .models import Nota
from .models import Avaliacao
from .models import PedidoDocumento
from .models import ResultadoDisciplina


class ObservacoesValidacaoForm(forms.Form):
    observacoes_validacao = forms.CharField(
        label='Observações',
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'rows': 4}
        )
    )


class SolicitarDocumentoForm(forms.Form):
    tipo = forms.ChoiceField(
        choices=PedidoDocumento.TIPO_CHOICES,
        widget=forms.RadioSelect,
    )
    ano_letivo = forms.ModelChoiceField(
        queryset=None,
        label='Ano Letivo',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from turmas.models import AnoLetivo
        self.fields['ano_letivo'].queryset = AnoLetivo.objects.all()


class ComprovativoPagamentoForm(forms.Form):
    comprovativo_pagamento = forms.ImageField(
        label='Comprovativo de Pagamento',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
    )


class ImportarNotasExcelForm(forms.Form):
    arquivo = forms.FileField(
        label='Arquivo Excel',
        help_text='Use o modelo da pauta e preencha as colunas MAC e NPT.',
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['npt'].help_text = (
            'No 3º trimestre este valor é substituído automaticamente pela '
            'média dos trimestres anteriores.'
        )

    def clean(self):
        cleaned_data = super().clean()
        avaliacao = cleaned_data.get('avaliacao')
        aluno = cleaned_data.get('aluno')

        if avaliacao and not avaliacao.periodo.periodo_lancamento_ativo():
            raise forms.ValidationError(
                'Fora do período de lançamento de notas para este trimestre.'
            )

        if avaliacao and aluno:
            nota_provisoria = Nota(
                pk=self.instance.pk, avaliacao=avaliacao, aluno=aluno
            )
            if nota_provisoria.eh_terceiro_trimestre():
                try:
                    nota_provisoria.calcular_npt_terceiro_trimestre()
                except ValueError as exc:
                    raise forms.ValidationError(str(exc))

        return cleaned_data

class LancamentoNotaForm(forms.Form):
    aluno_id = forms.IntegerField(widget=forms.HiddenInput())
    mac = forms.DecimalField(
        max_digits=4, decimal_places=1,
        min_value=0, max_value=20,
        required=False,
        widget=forms.NumberInput(
            attrs={'class': 'form-control form-control-sm', 'step': '0.1', 'data-campo': 'mac'}
        ),
    )
    npt = forms.DecimalField(
        max_digits=4, decimal_places=1,
        min_value=0, max_value=20,
        required=False,
        widget=forms.NumberInput(
            attrs={'class': 'form-control form-control-sm', 'step': '0.1', 'data-campo': 'npt'}
        ),
    )


LancamentoNotaFormSet = forms.formset_factory(LancamentoNotaForm, extra=0)


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
