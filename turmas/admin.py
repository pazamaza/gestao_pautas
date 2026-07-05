from django.contrib import admin

from .models import (
    AnoLetivo,
    PeriodoAcademico,
    Classe,
    Turma
)


@admin.register(AnoLetivo)
class AnoLetivoAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('descricao',)


@admin.register(PeriodoAcademico)
class PeriodoAcademicoAdmin(admin.ModelAdmin):
    list_display = (
        'nome', 'ano_letivo', 'aberto', 'data_inicio_lancamento', 'data_fim_lancamento'
    )
    list_filter = ('ano_letivo', 'aberto')
    search_fields = ('nome',)
    autocomplete_fields = ('ano_letivo',)


@admin.register(Classe)
class ClasseAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'classe', 'ano_letivo', 'ativo')
    list_filter = ('classe', 'ano_letivo', 'ativo')
    search_fields = ('nome',)
    autocomplete_fields = ('classe', 'ano_letivo')
