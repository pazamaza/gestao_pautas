from django.contrib import admin
from .models import Professor, AtribuicaoDocente, DiretorTurma


@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    list_display = ('numero_funcionario', '__str__', 'telefone', 'ativo')
    list_filter = ('ativo',)
    search_fields = (
        'numero_funcionario', 'user__first_name', 'user__last_name', 'user__username'
    )


@admin.register(AtribuicaoDocente)
class AtribuicaoDocenteAdmin(admin.ModelAdmin):
    list_display = ('professor', 'disciplina', 'turma', 'ano_letivo', 'ativo')
    list_filter = ('ano_letivo', 'disciplina', 'ativo')
    search_fields = (
        'professor__user__first_name', 'professor__user__last_name',
        'professor__numero_funcionario'
    )
    autocomplete_fields = ('professor', 'disciplina', 'turma', 'ano_letivo')


@admin.register(DiretorTurma)
class DiretorTurmaAdmin(admin.ModelAdmin):
    list_display = ('professor', 'turma', 'ano_letivo', 'ativo')
    list_filter = ('ano_letivo', 'ativo')
    search_fields = ('professor__user__first_name', 'professor__user__last_name')
    autocomplete_fields = ('professor', 'turma', 'ano_letivo')
