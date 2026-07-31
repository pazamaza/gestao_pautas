from decimal import Decimal

from alunos.models import Aluno
from disciplinas.models import Disciplina
from pautas.models import Nota, ResultadoDisciplina, SituacaoAnual
from pautas.services.periodos import campo_periodo


def gerar_resultados_finais():
    # ATENÇÃO: operação destrutiva — apaga TODOS os ResultadoDisciplina
    # existentes (de todos os alunos/anos) antes de os recriar a partir das
    # Notas actuais. É a única forma suportada de popular ResultadoDisciplina
    # em massa; para recalcular um único aluno/disciplina sem apagar o resto,
    # usar atualizar_resultado_disciplina() abaixo.
    ResultadoDisciplina.objects.all().delete()
    criados = 0

    alunos = Aluno.objects.filter(estado=Aluno.ESTADO_ATIVO).select_related('turma', 'turma__classe')

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


def _tem_ambas_nucleares_simultaneas(resultados_disciplina):
    """True se as DUAS disciplinas nucleares (Português e Matemática, ver
    Disciplina.nuclear) estiverem simultaneamente entre os
    `resultados_disciplina` dados (ex.: ambas na banda de tolerância ou de
    recurso). A "Base Legal" nega tolerância/recurso apenas quando isto
    acontece — uma disciplina nuclear sozinha na banda não bloqueia nada."""
    nucleares = {r.disciplina_id for r in resultados_disciplina if r.disciplina.nuclear}
    return len(nucleares) >= 2


def _transicao_primeiro_ano(resultados):
    # "Base Legal" — Iº Ano: aprova com MF>=10 em todas as disciplinas;
    # tolera até 2 disciplinas com MF entre 8-9, desde que não sejam
    # Português e Matemática simultaneamente. Faltas e MF<8 reprovam
    # sempre, sem excepção nem compensação.
    if any(r.resultado == ResultadoDisciplina.RESULTADO_REPROVADO_FALTAS for r in resultados):
        return SituacaoAnual.SITUACAO_REPROVADO, []

    if any(r.mf < 8 for r in resultados):
        return SituacaoAnual.SITUACAO_REPROVADO, []

    tolerancia = [r for r in resultados if 8 <= r.mf < 10]
    if len(tolerancia) > 2:
        return SituacaoAnual.SITUACAO_REPROVADO, []
    if tolerancia and _tem_ambas_nucleares_simultaneas(tolerancia):
        return SituacaoAnual.SITUACAO_REPROVADO, []
    if tolerancia:
        return SituacaoAnual.SITUACAO_APROVADO_COMPENSACAO, tolerancia
    return SituacaoAnual.SITUACAO_APROVADO, []


def _valor_decisivo(resultado):
    """Valor que decide a disciplina: a nota de recurso (NER), se já
    lançada — é nota seca e substitui a MFA por completo — senão a
    própria MFA (campo `mf`)."""
    return resultado.nota_recurso if resultado.nota_recurso is not None else resultado.mf


def _aplicar_veto_gatilho_recurso(resultados):
    """Fecha o recurso (força "Reprovado", grava no ResultadoDisciplina) a
    todas as disciplinas do aluno na banda 7-9 — pendentes ou já resolvidas
    por uma NER entretanto lançada — quando o gatilho é vetado:
    (a) alguma disciplina reprovou directamente, sem hipótese de recurso
        (MFA<=6, ou reprovação por faltas) — um aluno já condenado numa
        disciplina não tem razão para fazer recurso nas outras;
    (b) mais de 4 disciplinas na banda 7-9;
    (c) L.Portuguesa e Matemática simultaneamente nessa banda.
    Devolve True se o veto se aplica (mesmo que já não haja nada para
    fechar — ex.: recálculo repetido)."""
    candidatos = [r for r in resultados if r.mf is not None and 7 <= r.mf <= 9]
    if not candidatos:
        return False

    reprovado_sem_recurso = any(
        (r.mf is not None and r.mf <= 6)
        or r.resultado == ResultadoDisciplina.RESULTADO_REPROVADO_FALTAS
        for r in resultados
    )
    nucleares = [r for r in candidatos if r.disciplina.nuclear]
    if not reprovado_sem_recurso and len(candidatos) <= 4 and len(nucleares) < 2:
        return False

    a_fechar = [r for r in candidatos if r.resultado != ResultadoDisciplina.RESULTADO_REPROVADO]
    if a_fechar:
        for r in a_fechar:
            r.resultado = ResultadoDisciplina.RESULTADO_REPROVADO
        ResultadoDisciplina.objects.filter(pk__in=[r.pk for r in a_fechar]).update(
            resultado=ResultadoDisciplina.RESULTADO_REPROVADO
        )
    return True


def _transicao_segundo_ano(resultados):
    # IIº Ano EJA: mesma regra do Iº Ano (MFA>=10 em todas, tolerância de
    # até 2 disciplinas não-nucleares entre 8-9), com duas diferenças —
    # disciplinas com MFA 7-9 têm direito a Exame de Recurso (NER) primeiro,
    # para tentar corrigi-las ANTES desta verificação (ver
    # ResultadoDisciplina._verificar_resultado_segundo_ano); e uma única
    # disciplina nuclear (L.Port/Mat) na banda de tolerância já reprova —
    # não é preciso as duas estarem simultaneamente, como no Iº Ano.
    if _aplicar_veto_gatilho_recurso(resultados):
        return SituacaoAnual.SITUACAO_REPROVADO, []

    pendentes = [r for r in resultados if r.resultado == ResultadoDisciplina.RESULTADO_RECURSO]
    if pendentes:
        return None, []  # há disciplina(s) elegível(is) a recurso, ainda sem NER lançada

    if any(r.resultado == ResultadoDisciplina.RESULTADO_REPROVADO_FALTAS for r in resultados):
        return SituacaoAnual.SITUACAO_REPROVADO, []

    if any(_valor_decisivo(r) < 8 for r in resultados):
        # Só chega aqui quem já tentou o recurso e continuou abaixo de 8.
        return SituacaoAnual.SITUACAO_REPROVADO, []

    tolerancia = [r for r in resultados if 8 <= _valor_decisivo(r) < 10]
    if any(r.disciplina.nuclear for r in tolerancia):
        return SituacaoAnual.SITUACAO_REPROVADO, []
    if len(tolerancia) > 2:
        return SituacaoAnual.SITUACAO_REPROVADO, []
    if tolerancia:
        return SituacaoAnual.SITUACAO_APROVADO_COMPENSACAO, tolerancia
    return SituacaoAnual.SITUACAO_APROVADO, []


def verificar_transicao_aluno(aluno, ano_letivo):
    """Decide a Situação Anual do aluno segundo a "Base Legal EJA"
    (docs/processos_sistema.pdf), com regras distintas por Classe — ver
    _transicao_primeiro_ano / _transicao_segundo_ano. Devolve None quando
    ainda não há resultados, ou (IIº Ano) quando algum ainda aguarda Exame
    Nacional/nota de recurso — tal como o comportamento anterior quando não
    havia dados suficientes."""
    resultados = list(
        ResultadoDisciplina.objects
        .filter(aluno=aluno, ano_letivo=ano_letivo)
        .select_related('disciplina')
    )

    if not resultados:
        return None

    if aluno.turma.eh_segundo_ano():
        situacao, em_recurso = _transicao_segundo_ano(resultados)
    else:
        situacao, em_recurso = _transicao_primeiro_ano(resultados)

    if situacao is None:
        return None

    situacao_anual, _ = SituacaoAnual.objects.update_or_create(
        aluno=aluno,
        ano_letivo=ano_letivo,
        defaults={'situacao': situacao},
    )
    situacao_anual.disciplinas_em_deficiencia.set(
        [resultado.disciplina for resultado in em_recurso]
    )
    return situacao_anual


def _observacao_recurso(resultados_aluno, situacao_anual):
    """Texto para a coluna "Observação" da pauta geral — reservada apenas
    aos casos que passaram por recurso, para discriminar quem aprovou/
    reprovou directamente (fica em branco) de quem só aprovou/reprovou
    DEPOIS do recurso (fica identificado, com as disciplinas). Enquanto a
    disciplina está "Recurso" (pendente de NER) lista quais; resolvido o
    recurso (NER lançada ou vetada), o texto mantém-se — não volta a ficar
    em branco nem colapsa para um "Aprovado"/"Reprovado" genérico, que já é
    mostrado à parte na coluna "Situação Geral". Só o IIº Ano tem recurso —
    para quem nunca passou por lá isto fica sempre em branco."""
    pendentes = [r for r in resultados_aluno if r.resultado == ResultadoDisciplina.RESULTADO_RECURSO]
    if pendentes:
        nomes = ', '.join(sorted(r.disciplina.nome for r in pendentes))
        return f'Recurso: {nomes}'

    com_recurso = [r for r in resultados_aluno if r.nota_recurso is not None]
    if not com_recurso or not situacao_anual:
        return ''

    nomes = ', '.join(sorted(r.disciplina.nome for r in com_recurso))
    if situacao_anual.situacao == SituacaoAnual.SITUACAO_REPROVADO:
        return f'Reprovado após recurso: {nomes}'
    return f'Aprovado após recurso: {nomes}'


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

    linhas = []
    for aluno in alunos:
        celulas = [resultados.get((aluno.id, disciplina.id)) for disciplina in disciplinas]
        situacao_anual = verificar_transicao_aluno(aluno, ano_letivo)
        # Sem SituacaoAnual ainda (verificar_transicao_aluno devolveu None)
        # porque há pelo menos uma disciplina "Recurso" (IIº Ano) à espera
        # da NER — a coluna "Situação Geral" mostra isto em vez de "—".
        aguarda_recurso = not situacao_anual and any(
            c and c.resultado == ResultadoDisciplina.RESULTADO_RECURSO for c in celulas
        )
        linhas.append({
            'aluno': aluno,
            'celulas': celulas,
            'situacao_anual': situacao_anual,
            'aguarda_recurso': aguarda_recurso,
            'observacao': _observacao_recurso([c for c in celulas if c], situacao_anual),
        })

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
