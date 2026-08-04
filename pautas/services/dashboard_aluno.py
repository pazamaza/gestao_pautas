from decimal import Decimal

from turmas.models import PeriodoAcademico
from frequencias.models import Frequencia
from pautas.models import Avaliacao, Nota, ResultadoDisciplina
from pautas.services.periodos import campo_periodo

MEDIA_BOA = Decimal('14')
MEDIA_MINIMA = Decimal('10')
FREQUENCIA_MINIMA = 75
FREQUENCIA_BOA = 95


def _media(valores):
    valores = [v for v in valores if v is not None]
    if not valores:
        return None
    return round(sum(valores) / len(valores), 1)


def _status_assiduidade(frequencia):
    if frequencia >= FREQUENCIA_BOA:
        return 'Excelente'
    if frequencia >= FREQUENCIA_MINIMA:
        return 'Bom'
    return 'Insuficiente'


def _frequencia_por_disciplina(aluno, disciplina):
    registos = Frequencia.objects.filter(aluno=aluno, atribuicao__disciplina=disciplina)
    total = registos.count()
    if total == 0:
        return None
    presentes = registos.filter(estado__in=[Frequencia.PRESENTE, Frequencia.ATRASO]).count()
    return round(presentes / total * 100, 1)


def _trimestres_validados_por_disciplina(aluno):
    """{disciplina_id: {'mt1', 'mt2', ...}} com os trimestres cuja Avaliacao já
    foi validada — usado no gráfico de notas para não esperar pela validação
    anual do ResultadoDisciplina (mais lenta) nem mostrar zero para um
    trimestre que ainda não foi lançado/publicado."""
    avaliacoes = (
        Avaliacao.objects
        .filter(atribuicao__turma=aluno.turma, status=Avaliacao.STATUS_VALIDADA)
        .select_related('periodo', 'atribuicao')
    )
    mapa = {}
    for avaliacao in avaliacoes:
        campo = campo_periodo(avaliacao.periodo)
        if campo:
            mapa.setdefault(avaliacao.atribuicao.disciplina_id, set()).add(campo)
    return mapa


def _avaliacoes_periodo_atual(aluno):
    periodo_atual = (
        PeriodoAcademico.objects.filter(ano_letivo=aluno.turma.ano_letivo, aberto=True)
        .order_by('-id').first()
    )
    if not periodo_atual:
        return periodo_atual, []

    avaliacoes = (
        Avaliacao.objects
        .filter(periodo=periodo_atual, atribuicao__turma=aluno.turma)
        .select_related('atribuicao__disciplina', 'atribuicao__professor__user')
        .order_by('atribuicao__disciplina__nome')
    )
    return periodo_atual, list(avaliacoes)


def estatisticas_aluno(aluno):
    # `resultados` (ResultadoDisciplina.status == validada) é a validação
    # ANUAL, um passo administrativo manual e mais lento — ver
    # `pautas/views.py:_pautas_validadas_do_aluno`, que já usa o mesmo
    # critério de "trimestres validados" abaixo para mostrar as notas em
    # "Minhas Pautas" antes dessa validação anual acontecer (só o bloco
    # "Resultado Final" espera por ela). O resumo do dashboard segue a
    # mesma lógica: uma disciplina conta para a média/evolução assim que
    # os seus 3 trimestres têm Avaliacao validada, sem esperar pelo
    # "carimbo" administrativo anual.
    resultados = (
        ResultadoDisciplina.objects
        .filter(aluno=aluno, status=ResultadoDisciplina.STATUS_VALIDADA)
        .select_related('disciplina')
        .order_by('disciplina__nome')
    )

    todos_resultados = (
        ResultadoDisciplina.objects
        .filter(aluno=aluno)
        .select_related('disciplina')
        .order_by('disciplina__nome')
    )
    trimestres_validados = _trimestres_validados_por_disciplina(aluno)

    def _trimestres_da_disciplina(resultado):
        return trimestres_validados.get(resultado.disciplina_id, set())

    def _valor_trimestre(resultado, campo):
        if campo not in _trimestres_da_disciplina(resultado):
            return None
        return float(getattr(resultado, campo))

    resultados_publicados = [
        r for r in todos_resultados
        if {'mt1', 'mt2', 'mt3'}.issubset(_trimestres_da_disciplina(r))
    ]

    frequencia = aluno.calcular_frequencia()
    faltas = aluno.total_faltas()

    dias_letivos = aluno.frequencia_set.count()
    dias_presentes = aluno.frequencia_set.filter(estado__in=['P', 'A']).count()
    dias_ausentes = dias_letivos - dias_presentes

    media_geral = None
    if resultados_publicados:
        media_geral = (
            sum((resultado.mf for resultado in resultados_publicados), Decimal('0'))
            / len(resultados_publicados)
        )
        media_geral = media_geral.quantize(Decimal('0.1'))

    mensagens = []

    if media_geral is not None:
        if media_geral >= MEDIA_BOA:
            mensagens.append({
                'tipo': 'sucesso',
                'texto': (
                    f'Parabéns! A sua média geral é {media_geral}, um excelente resultado. '
                    'Continue assim!'
                ),
            })
        elif media_geral >= MEDIA_MINIMA:
            mensagens.append({
                'tipo': 'info',
                'texto': (
                    f'A sua média geral é {media_geral}. Está aprovado, mas há espaço para '
                    'melhorar — continue a estudar.'
                ),
            })
        else:
            mensagens.append({
                'tipo': 'alerta',
                'texto': (
                    f'A sua média geral é {media_geral}, abaixo do necessário para aprovação. '
                    'Procure apoio dos seus professores.'
                ),
            })

    for resultado in resultados_publicados:
        if resultado.mf < MEDIA_MINIMA:
            mensagens.append({
                'tipo': 'alerta',
                'texto': (
                    f'{resultado.disciplina.nome}: média {resultado.mf} — recomenda-se '
                    'reforço nesta disciplina.'
                ),
            })

    if frequencia < FREQUENCIA_MINIMA:
        mensagens.append({
            'tipo': 'alerta',
            'texto': (
                f'A sua frequência é de {frequencia}%, abaixo dos {FREQUENCIA_MINIMA}% '
                'exigidos — risco de reprovação por faltas.'
            ),
        })
    elif frequencia >= FREQUENCIA_BOA:
        mensagens.append({
            'tipo': 'sucesso',
            'texto': f'Excelente assiduidade: {frequencia}% de frequência!',
        })

    # Uma nota por disciplina (a mais recente) — nunca os últimos N registos
    # em bruto, que repetiam disciplinas com várias notas recentes e
    # deixavam de fora disciplinas com notas mais antigas.
    notas_validadas = (
        Nota.objects
        .filter(aluno=aluno, avaliacao__status=Avaliacao.STATUS_VALIDADA)
        .select_related('avaliacao__atribuicao__disciplina', 'avaliacao__atribuicao__professor__user')
        .order_by('avaliacao__atribuicao__disciplina_id', '-avaliacao__validado_em', '-criado_em')
    )
    disciplinas_vistas = set()
    ultimas_notas = []
    for nota in notas_validadas:
        disciplina_id = nota.avaliacao.atribuicao.disciplina_id
        if disciplina_id in disciplinas_vistas:
            continue
        disciplinas_vistas.add(disciplina_id)
        ultimas_notas.append({
            'disciplina': nota.avaliacao.atribuicao.disciplina,
            'professor': nota.avaliacao.atribuicao.professor,
            'nota': nota.mt,
            'aprovado': nota.mt >= MEDIA_MINIMA,
            '_recencia': nota.avaliacao.validado_em or nota.criado_em,
        })
    ultimas_notas.sort(key=lambda item: item['_recencia'], reverse=True)
    for item in ultimas_notas:
        del item['_recencia']

    evolucao_labels = ['1º Trimestre', '2º Trimestre', '3º Trimestre']
    evolucao_dados = [
        _media(float(r.mt1) for r in resultados_publicados) or 0,
        _media(float(r.mt2) for r in resultados_publicados) or 0,
        _media(float(r.mt3) for r in resultados_publicados) or 0,
    ]

    pautas_recentes = [
        {
            'disciplina': resultado.disciplina,
            'mf': resultado.mf,
            'frequencia': _frequencia_por_disciplina(aluno, resultado.disciplina),
        }
        for resultado in resultados_publicados
    ]

    periodo_atual, avaliacoes_periodo = _avaliacoes_periodo_atual(aluno)

    return {
        'resultados': resultados,
        'media_geral': media_geral,
        'frequencia': frequencia,
        'faltas': faltas,
        'mensagens': mensagens,
        'grafico_disciplinas_labels': [r.disciplina.nome for r in todos_resultados],
        'grafico_mt1': [_valor_trimestre(r, 'mt1') for r in todos_resultados],
        'grafico_mt2': [_valor_trimestre(r, 'mt2') for r in todos_resultados],
        'grafico_mt3': [_valor_trimestre(r, 'mt3') for r in todos_resultados],
        'dias_letivos': dias_letivos,
        'dias_presentes': dias_presentes,
        'dias_ausentes': dias_ausentes,
        'status_assiduidade': _status_assiduidade(frequencia),
        'ultimas_notas': ultimas_notas,
        'evolucao_labels': evolucao_labels,
        'evolucao_dados': evolucao_dados,
        'pautas_recentes': pautas_recentes,
        'periodo_atual': periodo_atual,
        'avaliacoes_periodo': avaliacoes_periodo,
    }
