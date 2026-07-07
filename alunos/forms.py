from django import forms
from django.db.models import Q
from .models import Aluno
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

    def clean_numero_processo(self):
        numero = self.cleaned_data['numero_processo' ]
        if Aluno.objects.filter(numero_processo=numero
            ).exclude(pk=self.instance.pk ).exists():
            raise forms.ValidationError('Já existe um aluno com este número.')
        return numero
    
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

def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self.fields['data_nascimento'].input_formats = [
        '%Y-%m-%d'
    ]

    if self.instance and self.instance.pk:
        self.initial['data_nascimento'] = (
            self.instance.data_nascimento.strftime('%Y-%m-%d')
        )