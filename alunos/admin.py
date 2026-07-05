from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Encarregado,
    Aluno,
    Matricula
)


@admin.register(Encarregado)
class EncarregadoAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'telefone', 'profissao')
    search_fields = ('user__first_name', 'user__last_name', 'user__username')


@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = (
        'numero_processo', 'nome', 'idade_calculada', 'turma', 'encarregado', 'estado',
        'foto_preview'
    )
    list_filter = ('turma', 'estado', 'sexo')
    search_fields = ('nome', 'numero_processo')
    autocomplete_fields = ('encarregado', 'turma')
    readonly_fields = ('foto_preview', 'idade_calculada', 'criado_em', 'atualizado_em')
    fieldsets = (
        (None, {
            'fields': (
                'nome', 'numero_processo', 'data_nascimento', 'idade_calculada', 'sexo',
                'foto', 'foto_preview'
            )
        }),
        ('Vínculos', {
            'fields': ('user', 'turma', 'encarregado', 'estado')
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


@admin.register(Matricula)
class MatriculaAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'turma', 'ano_letivo', 'data_matricula', 'ativa')
    list_filter = ('ano_letivo', 'ativa')
    search_fields = ('aluno__nome', 'aluno__numero_processo')
    autocomplete_fields = ('aluno',)
