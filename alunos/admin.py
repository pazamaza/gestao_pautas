from django import forms
from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.html import format_html

from .models import (
    Encarregado,
    Aluno,
    Matricula
)


class EncarregadoAdminForm(forms.ModelForm):
    class Meta:
        model = Encarregado
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.filter(
            groups__name='Encarregado'
        ).filter(
            Q(encarregado__isnull=True) | Q(pk=self.instance.user_id)
        ).distinct().order_by('first_name', 'last_name')

    def clean_user(self):
        user = self.cleaned_data['user']
        if not user.first_name:
            raise forms.ValidationError(
                'Este utilizador não tem nome preenchido. '
                'Preencha o nome e apelido antes de o associar como encarregado.'
            )
        return user


@admin.register(Encarregado)
class EncarregadoAdmin(admin.ModelAdmin):
    form = EncarregadoAdminForm
    list_display = ('__str__', 'telefone', 'profissao')
    search_fields = ('user__first_name', 'user__last_name', 'user__username')


class AlunoAdminForm(forms.ModelForm):
    class Meta:
        model = Aluno
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.filter(
            groups__name='Aluno'
        ).order_by('first_name', 'last_name')
        self.fields['user'].required = True

        self.fields['encarregado'].queryset = Encarregado.objects.filter(
            user__groups__name='Encarregado'
        ).select_related('user').order_by('user__first_name', 'user__last_name')

    def clean_user(self):
        user = self.cleaned_data['user']
        if not user.get_full_name():
            raise forms.ValidationError(
                'Este utilizador não tem nome preenchido. '
                'Preencha o nome e apelido antes de o associar como aluno.'
            )
        return user


@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    form = AlunoAdminForm
    list_display = (
        'numero_processo', 'nome', 'idade_calculada', 'turma', 'encarregado', 'estado',
        'foto_preview'
    )
    list_filter = ('turma', 'estado', 'sexo')
    search_fields = ('nome', 'numero_processo')
    autocomplete_fields = ('encarregado', 'turma')
    readonly_fields = ('nome', 'foto_preview', 'idade_calculada', 'criado_em', 'atualizado_em')
    fieldsets = (
        (None, {
            'fields': (
                'user', 'nome', 'numero_processo', 'data_nascimento', 'idade_calculada', 'sexo',
                'foto', 'foto_preview'
            )
        }),
        ('Vínculos', {
            'fields': ('turma', 'encarregado', 'estado')
        }),
        ('Registo', {
            'fields': ('criado_em', 'atualizado_em')
        }),
    )

    def foto_preview(self, obj):
        if obj.foto:
            return format_html(
                '<img src="{}" style="height:60px;border-radius:4px;" />',
                obj.foto.url
            )
        return '—'
    foto_preview.short_description = 'Foto'

    def idade_calculada(self, obj):
        return obj.calcular_idade()
    idade_calculada.short_description = 'Idade'

    def save_model(self, request, obj, form, change):
        if obj.user_id:
            obj.nome = obj.user.get_full_name() or obj.user.username
        super().save_model(request, obj, form, change)


@admin.register(Matricula)
class MatriculaAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'turma', 'ano_letivo', 'data_matricula', 'ativa')
    list_filter = ('ano_letivo', 'ativa')
    search_fields = ('aluno__nome', 'aluno__numero_processo')
    autocomplete_fields = ('aluno',)
