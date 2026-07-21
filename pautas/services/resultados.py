from decimal import Decimal

from alunos.models import Aluno
from disciplinas.models import Disciplina
from pautas.models import Nota, ResultadoDisciplina, SituacaoAnual
from pautas.services.periodos import campo_periodo

DISCIPLINAS_EM_ANDAMENTO = (
    ResultadoDisciplina.RESULTADO_RECURSO,
    ResultadoDisciplina.RESULTADO_DEFICIENCIA,
)

LIMITE_FALTAS_INJUSTIFICADAS = 9


def gerar_resultados_finais():
    # ATENÇÃO: operação destrutiva — apaga TODOS os ResultadoDisciplina
    # existentes (de todos os alunos/anos) antes de os recriar a partir das
    # Notas actuais. É a única forma suportada de popular ResultadoDisciplina
    # em massa; para recalcular um único aluno/disciplina sem apagar o resto,
    # usar atualizar_resultado_disciplina() abaixo.
    ResultadoDisciplina.objects.all().delete()
    criados = 0

    alunos = Aluno.objects.filter(estado=Aluno.ESTADO_ATIVO).select_related('turma')

    for aluno in alunos:
        notas_aluno = (
            Nota.objects
            .filter(aluno=aluno)
            .select_related(
                'avaliacao__periodo',
                'avaliacao__atribuicao__disciplina',
                'avaliacao__atribuicao__ano_letivo',
            )
        )

        disciplinas = {}
        for nota in notas_aluno:
            disciplina = nota.avaliacao.atribuicao.disciplina
            disciplinas.setdefault(disciplina.id, {
                'disciplina': disciplina,
                'ano_letivo': nota.avaliacao.atribuicao.ano_letivo,
                'mt1': Decimal('0'),
                'mt2': Decimal('0'),
                'mt3': Decimal('0'),
            })

            campo = campo_periodo(nota.avaliacao.periodo)
            if campo:
                disciplinas[disciplina.id][campo] = nota.mt

        for dados in disciplinas.values():
            ResultadoDisciplina.objects.create(
                aluno=aluno,
                disciplina=dados['disciplina'],
                ano_letivo=dados['ano_letivo'],
                mt1=dados['mt1'],
                mt2=dados['mt2'],
                mt3=dados['mt3'],
            )
            criados += 1

    return criados


def atualizar_resultado_disciplina(aluno, disciplina, ano_letivo):
    """Recalcula mt1/mt2/mt3 de UM ResultadoDisciplina a partir das Notas
    existentes, sem apagar/recriar as restantes linhas nem alterar o
    status de validação já atribuído (ao contrário de gerar_resultados_finais)."""
    notas = Nota.objects.filter(
        aluno=aluno,
        avaliacao__atribuicao__disciplina=disciplina,
        avaliacao__atribuicao__ano_letivo=ano_letivo,
    ).select_related('avaliacao__periodo')

    valores = {'mt1': Decimal('0'), 'mt2': Decimal('0'), 'mt3': Decimal('0')}
    for nota in notas:
        campo = campo_periodo(nota.avaliacao.periodo)
        if campo:
            valores[campo] = nota.mt

    resultado, _ = ResultadoDisciplina.objects.get_or_create(
        aluno=aluno, disciplina=disciplina, ano_letivo=ano_letivo,
    )
    resultado.mt1 = valores['mt1']
    resultado.mt2 = valores['mt2']
    resultado.mt3 = valores['mt3']
    resultado.save()
    return resultado


def verificar_transicao_aluno(aluno, ano_letivo):
    # Regra de negócio mais complexa do sistema: decide se o aluno transita
    # de ano. Ordem de decisão:
    # 1) Reprovação automática por faltas: >= LIMITE_FALTAS_INJUSTIFICADAS
    #    (9) faltas injustificadas no ano letivo reprova o aluno de imediato,
    #    independentemente das notas em qualquer disciplina.
    # 2) Se alguma disciplina tem resultado "Reprovado" -> reprovado (sem
    #    hipótese de compensação).
    # 3) Caso contrário, olha-se para as disciplinas "em andamento"
    #    (resultado 'Recurso' ou 'Deficiência' — ver DISCIPLINAS_EM_ANDAMENTO):
    #    - 0 disciplinas em andamento -> aprovado.
    #    - 1 ou 2 disciplinas -> aprovado por compensação directa (não é
    #      preciso ter nota de recurso lançada).
    #    - 3 ou 4 disciplinas -> só aprovado por compensação se pelo menos
    #      2 delas já tiverem nota_recurso >= 10; senão reprovado.
    #    - mais de 4 disciplinas em andamento -> reprovado.
    if aluno.contar_faltas_injustificadas(ano_letivo=ano_letivo) >= LIMITE_FALTAS_INJUSTIFICADAS:
        situacao_anual, _ = SituacaoAnual.objects.update_or_create(
            aluno=aluno,
            ano_letivo=ano_letivo,
            defaults={'situacao': SituacaoAnual.SITUACAO_REPROVADO},
        )
        situacao_anual.disciplinas_em_deficiencia.clear()
        return situacao_anual

    resultados = list(
        ResultadoDisciplina.objects
        .filter(aluno=aluno, ano_letivo=ano_letivo)
        .select_related('disciplina')
    )

    if not resultados:
        return None

    if any(resultado.resultado == ResultadoDisciplina.RESULTADO_REPROVADO for resultado in resultados):
        situacao = SituacaoAnual.SITUACAO_REPROVADO
        em_deficiencia = []
    else:
        em_deficiencia = [
            resultado for resultado in resultados
            if resultado.resultado in DISCIPLINAS_EM_ANDAMENTO
        ]

        if not em_deficiencia:
            situacao = SituacaoAnual.SITUACAO_APROVADO
        elif len(em_deficiencia) <= 2:
            situacao = SituacaoAnual.SITUACAO_APROVADO_COMPENSACAO
        elif len(em_deficiencia) <= 4:
            recuperadas = sum(
                1 for resultado in em_deficiencia
                if resultado.nota_recurso is not None and resultado.nota_recurso >= 10
            )
            situacao = (
                SituacaoAnual.SITUACAO_APROVADO_COMPENSACAO
                if recuperadas >= 2
                else SituacaoAnual.SITUACAO_REPROVADO
            )
        else:
            situacao = SituacaoAnual.SITUACAO_REPROVADO

    situacao_anual, _ = SituacaoAnual.objects.update_or_create(
        aluno=aluno,
        ano_letivo=ano_letivo,
        defaults={'situacao': situacao},
    )
    situacao_anual.disciplinas_em_deficiencia.set(
        [resultado.disciplina for resultado in em_deficiencia]
    )
    return situacao_anual


def montar_pauta_final_turma(turma, ano_letivo):
    disciplinas = Disciplina.objects.filter(
        atribuicaodocente__turma=turma,
        atribuicaodocente__ano_letivo=ano_letivo,
        atribuicaodocente__ativo=True,
    ).distinct().order_by('nome')

    alunos = Aluno.objects.filter(turma=turma, estado=Aluno.ESTADO_ATIVO).order_by('nome')

    resultados = {
        (resultado.aluno_id, resultado.disciplina_id): resultado
        for resultado in ResultadoDisciplina.objects.filter(
            aluno__turma=turma, ano_letivo=ano_letivo
        ).select_related('disciplina', 'aluno')
    }

    linhas = [
        {
            'aluno': aluno,
            'celulas': [resultados.get((aluno.id, disciplina.id)) for disciplina in disciplinas],
            'situacao_anual': verificar_transicao_aluno(aluno, ano_letivo),
        }
        for aluno in alunos
    ]

    return disciplinas, linhas


def montar_mini_pauta_disciplina(disciplina, turma, ano_letivo):
    alunos = Aluno.objects.filter(turma=turma, estado=Aluno.ESTADO_ATIVO).order_by('nome')

    notas = (
        Nota.objects
        .filter(
            aluno__turma=turma,
            avaliacao__atribuicao__disciplina=disciplina,
            avaliacao__atribuicao__ano_letivo=ano_letivo,
        )
        .select_related('avaliacao__periodo')
    )

    notas_por_aluno = {}
    for nota in notas:
        campo = campo_periodo(nota.avaliacao.periodo)
        if not campo:
            continue
        notas_por_aluno.setdefault(nota.aluno_id, {})[campo] = nota

    resultados = {
        resultado.aluno_id: resultado
        for resultado in ResultadoDisciplina.objects.filter(
            aluno__turma=turma, disciplina=disciplina, ano_letivo=ano_letivo
        )
    }

    linhas = []
    for aluno in alunos:
        dados_periodos = notas_por_aluno.get(aluno.id, {})
        linhas.append({
            'aluno': aluno,
            'faltas': aluno.contar_faltas_injustificadas(
                ano_letivo=ano_letivo, disciplina=disciplina, turma=turma
            ),
            'mt1': dados_periodos.get('mt1'),
            'mt2': dados_periodos.get('mt2'),
            'mt3': dados_periodos.get('mt3'),
            'resultado': resultados.get(aluno.id),
        })

    return linhas


def gerar_situacoes_anuais(ano_letivo):
    alunos = Aluno.objects.filter(
        estado=Aluno.ESTADO_ATIVO,
        resultadodisciplina__ano_letivo=ano_letivo,
    ).distinct()

    total = 0
    for aluno in alunos:
        if verificar_transicao_aluno(aluno, ano_letivo):
            total += 1

    return total
