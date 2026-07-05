from django.contrib import admin

from .models import (
    Avaliacao,
    Nota,
    Pauta,
    LinhaPauta,
    ResultadoDisciplina,
    ResultadoFinal,
)


class SomenteLeituraAdmin(admin.ModelAdmin):
    """Lançamento e validação de notas são tarefas exclusivas dos professores
    e do fluxo de validação já existente nas views da aplicação (período de
    lançamento, professor titular, marcar_validada/marcar_com_erros). O admin
    do Django serve só para consulta/auditoria, nunca para editar."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Avaliacao)
class AvaliacaoAdmin(SomenteLeituraAdmin):
    list_display = ('atribuicao', 'periodo', 'status', 'validado_por', 'validado_em')
    list_filter = ('status', 'periodo__ano_letivo', 'periodo')
    search_fields = (
        'atribuicao__professor__user__first_name',
        'atribuicao__professor__user__last_name',
        'atribuicao__disciplina__nome',
        'atribuicao__turma__nome',
    )


@admin.register(Nota)
class NotaAdmin(SomenteLeituraAdmin):
    list_display = ('aluno', 'avaliacao', 'mac', 'npp', 'npt', 'mt')
    list_filter = ('avaliacao__periodo', 'avaliacao__atribuicao__disciplina')
    search_fields = ('aluno__nome', 'aluno__numero_processo')


@admin.register(Pauta)
class PautaAdmin(SomenteLeituraAdmin):
    list_display = ('atribuicao', 'periodo', 'fechada', 'criada_em')
    list_filter = ('periodo', 'fechada')


@admin.register(LinhaPauta)
class LinhaPautaAdmin(SomenteLeituraAdmin):
    list_display = ('pauta', 'aluno', 'media', 'aprovado')
    list_filter = ('aprovado',)
    search_fields = ('aluno__nome', 'aluno__numero_processo')


@admin.register(ResultadoDisciplina)
class ResultadoDisciplinaAdmin(SomenteLeituraAdmin):
    list_display = (
        'aluno', 'disciplina', 'ano_letivo', 'mt1', 'mt2', 'mt3', 'mf',
        'exame', 'nota_final', 'resultado', 'status'
    )
    list_filter = ('status', 'ano_letivo', 'disciplina', 'resultado')
    search_fields = ('aluno__nome', 'aluno__numero_processo')


@admin.register(ResultadoFinal)
class ResultadoFinalAdmin(SomenteLeituraAdmin):
    list_display = (
        'aluno', 'disciplina', 'ano_letivo', 'mt1', 'mt2', 'mt3', 'cf', 'exame', 'situacao'
    )
    list_filter = ('ano_letivo', 'disciplina', 'situacao')
    search_fields = ('aluno__nome', 'aluno__numero_processo')
