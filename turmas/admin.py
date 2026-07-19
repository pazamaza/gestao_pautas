from django.contrib import admin

from .models import (
    AnoLetivo,
    PeriodoAcademico,
    Classe,
    Turma,
    HorarioAula
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
    list_display = (
        'nome', 'classe', 'ano_letivo', 'sala', 'periodo', 'numero_pauta', 'numero_alunos', 'ativo'
    )
    list_filter = ('classe', 'ano_letivo', 'periodo', 'ativo')
    search_fields = ('nome', 'sala')
    autocomplete_fields = ('classe', 'ano_letivo')
    readonly_fields = ('numero_alunos',)

    def numero_alunos(self, obj):
        return obj.contar_alunos()
    numero_alunos.short_description = 'Nº Alunos'


@admin.register(HorarioAula)
class HorarioAulaAdmin(admin.ModelAdmin):
    list_display = ('turma', 'dia_semana', 'tempo', 'disciplina_nome', 'professor_nome')
    list_filter = ('turma', 'dia_semana')
    ordering = ('turma', 'dia_semana', 'tempo')
    autocomplete_fields = ('turma', 'atribuicao')

    def disciplina_nome(self, obj):
        return obj.atribuicao.disciplina if obj.atribuicao else 'Livre'
    disciplina_nome.short_description = 'Disciplina'

    def professor_nome(self, obj):
        return obj.atribuicao.professor if obj.atribuicao else '-'
    professor_nome.short_description = 'Professor'
