from django import forms
from django.db.models import Q
from .models import Aluno, Encarregado, Reclamacao
from django.contrib.auth.models import User


class AlunoForm(forms.ModelForm):
    class Meta:
        model = Aluno
        fields = '__all__'
        widgets = {
            'user': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            ),
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
    format='%Y-%m-%d',
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].label = 'Conta de utilizador (login) do aluno'
        self.fields['user'].queryset = User.objects.filter(
            groups__name='Aluno'
        ).filter(
            Q(aluno__isnull=True) | Q(pk=self.instance.user_id)
        ).distinct().order_by('first_name', 'last_name')

        self.fields['data_nascimento'].input_formats = ['%Y-%m-%d']
        if self.instance and self.instance.pk:
            self.initial['data_nascimento'] = (
                self.instance.data_nascimento.strftime('%Y-%m-%d')
            )

    def clean_numero_processo(self):
        numero = self.cleaned_data['numero_processo' ]
        if Aluno.objects.filter(numero_processo=numero
            ).exclude(pk=self.instance.pk ).exists():
            raise forms.ValidationError('Já existe um aluno com este número.')
        return numero
    
class DadosCertificadoForm(forms.ModelForm):
    class Meta:
        model = Aluno
        fields = [
            'nome_pai', 'nome_mae', 'naturalidade', 'municipio_natural', 'provincia_natal',
            'numero_bi', 'local_emissao_bi', 'data_emissao_bi', 'foto_bi',
        ]
        widgets = {
            'nome_pai': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_mae': forms.TextInput(attrs={'class': 'form-control'}),
            'naturalidade': forms.TextInput(attrs={'class': 'form-control'}),
            'municipio_natural': forms.TextInput(attrs={'class': 'form-control'}),
            'provincia_natal': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_bi': forms.TextInput(attrs={'class': 'form-control'}),
            'local_emissao_bi': forms.TextInput(attrs={'class': 'form-control'}),
            'data_emissao_bi': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-control', 'type': 'date'},
            ),
            'foto_bi': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'naturalidade': 'Naturalidade (cidade/comuna de nascimento)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_emissao_bi'].input_formats = ['%Y-%m-%d']
        if self.instance and self.instance.data_emissao_bi:
            self.initial['data_emissao_bi'] = self.instance.data_emissao_bi.strftime('%Y-%m-%d')

        # Nome do pai fica opcional (pode não se aplicar); os restantes são
        # exigidos para o certificado. O B.I. só é obrigatório anexar uma
        # vez — depois disso o aluno pode editar os outros campos sem ter
        # de voltar a carregar o ficheiro.
        for campo in (
            'nome_mae', 'naturalidade', 'municipio_natural', 'provincia_natal',
            'numero_bi', 'local_emissao_bi', 'data_emissao_bi',
        ):
            self.fields[campo].required = True
        if not (self.instance and self.instance.foto_bi):
            self.fields['foto_bi'].required = True


class EncarregadoCadastroForm(forms.Form):

    first_name = forms.CharField(
        label='Nome',
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    last_name = forms.CharField(
        label='Apelido',
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    username = forms.CharField(
        label='Utilizador',
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={'class': 'form-control'}
        )
    )

    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(
            attrs={'class': 'form-control'}
        )
    )

    telefone = forms.CharField(
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    profissao = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )


class EncarregadoEdicaoForm(forms.Form):

    first_name = forms.CharField(
        label='Nome',
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    last_name = forms.CharField(
        label='Apelido',
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={'class': 'form-control'}
        )
    )

    telefone = forms.CharField(
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    profissao = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

class ReclamacaoForm(forms.ModelForm):
    class Meta:
        model = Reclamacao
        fields = ['encarregado', 'aluno', 'motivo']
        widgets = {
            'encarregado': forms.Select(attrs={'class': 'form-select'}),
            'aluno': forms.Select(attrs={'class': 'form-select'}),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['encarregado'].queryset = Encarregado.objects.select_related('user').order_by(
            'user__first_name', 'user__last_name'
        )
        self.fields['aluno'].required = False


class EncaminharReclamacaoForm(forms.Form):
    encaminhado_para = forms.ChoiceField(
        label='Encaminhar para',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    def __init__(self, *args, destinos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['encaminhado_para'].choices = destinos or []


class ResolverReclamacaoForm(forms.Form):
    observacoes_resolucao = forms.CharField(
        label='Observações da resolução',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )
