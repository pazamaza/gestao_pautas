from professores.models import AtribuicaoDocente
from turmas.models import PeriodoAcademico

LIMITE_FALTAS_POR_TEMPOS_SEMANAIS = {
    1: 3,
    2: 4,
}
LIMITE_FALTAS_PADRAO = 5  # mais de 2 tempos lectivos semanais


def limite_faltas_trimestre(atribuicao):
    tempos = atribuicao.horarios.count()
    return LIMITE_FALTAS_POR_TEMPOS_SEMANAIS.get(tempos, LIMITE_FALTAS_PADRAO)


def aluno_excedeu_faltas_disciplina(aluno, disciplina, ano_letivo):
    """Regra de faltas da "Base Legal EJA": o aluno reprova a disciplina se,
    em QUALQUER trimestre, o nº de faltas injustificadas atingir o limite
    definido pela carga horária semanal da disciplina (3 se 1 tempo/semana,
    4 se 2 tempos, 5 se mais de 2 tempos).

    Usa data_inicio_lancamento/data_fim_lancamento de cada PeriodoAcademico
    como fronteira do trimestre (não existe outro campo de calendário
    lectivo no sistema); trimestres sem essas datas preenchidas são
    ignorados nesta contagem (não há como saber a que trimestre pertence
    uma falta sem essas datas).
    """
    from frequencias.models import Frequencia

    atribuicoes = AtribuicaoDocente.objects.filter(
        disciplina=disciplina, turma=aluno.turma, ano_letivo=ano_letivo,
    )
    if not atribuicoes.exists():
        return False

    periodos = PeriodoAcademico.objects.filter(ano_letivo=ano_letivo)

    for atribuicao in atribuicoes:
        limite = limite_faltas_trimestre(atribuicao)
        for periodo in periodos:
            if not periodo.data_inicio_lancamento or not periodo.data_fim_lancamento:
                continue
            frequencias_periodo = Frequencia.objects.filter(
                aluno=aluno,
                atribuicao=atribuicao,
                estado=Frequencia.FALTA,
                data__gte=periodo.data_inicio_lancamento,
                data__lte=periodo.data_fim_lancamento,
            ).select_related('justificacaofalta')
            # esta_injustificada() exclui faltas ainda dentro do prazo de
            # justificação e faltas já com JustificacaoFalta aprovada — sem
            # isto, um aluno com falta devidamente justificada seria
            # reprovado na mesma (mesmo bug que Aluno.contar_faltas_injustificadas
            # já evita, em alunos/models.py, para a mesma regra).
            faltas = sum(1 for f in frequencias_periodo if f.esta_injustificada())
            if faltas >= limite:
                return True

    return False
