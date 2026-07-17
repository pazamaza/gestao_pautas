from django.contrib import admin
from .models import Frequencia, JustificacaoFalta


@admin.register(Frequencia)
class FrequenciaAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'atribuicao', 'data', 'estado')
    list_filter = ('estado', 'data', 'atribuicao__turma', 'atribuicao__disciplina')
    search_fields = ('aluno__nome', 'aluno__numero_processo')
    autocomplete_fields = ('aluno', 'atribuicao')
    date_hierarchy = 'data'


@admin.register(JustificacaoFalta)
class JustificacaoFaltaAdmin(admin.ModelAdmin):
    list_display = ('frequencia', 'data_submissao', 'aprovada')
    list_filter = ('aprovada', 'data_submissao')
    search_fields = ('frequencia__aluno__nome',)
    autocomplete_fields = ('frequencia',)
