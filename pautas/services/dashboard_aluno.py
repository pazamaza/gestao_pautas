from decimal import Decimal

from turmas.models import PeriodoAcademico
from frequencias.models import Frequencia
from pautas.models import Avaliacao, Nota, ResultadoDisciplina

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
    resultados = (
        ResultadoDisciplina.objects
        .filter(aluno=aluno, status=ResultadoDisciplina.STATUS_VALIDADA)
        .select_related('disciplina')
        .order_by('disciplina__nome')
    )

    frequencia = aluno.calcular_frequencia()
    faltas = aluno.total_faltas()

    dias_letivos = aluno.frequencia_set.count()
    dias_presentes = aluno.frequencia_set.filter(estado__in=['P', 'A']).count()
    dias_ausentes = dias_letivos - dias_presentes

    media_geral = None
    if resultados:
        media_geral = (
            sum((resultado.mf for resultado in resultados), Decimal('0')) / len(resultados)
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

    for resultado in resultados:
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

    notas_recentes = (
        Nota.objects
        .filter(aluno=aluno, avaliacao__status=Avaliacao.STATUS_VALIDADA)
        .select_related('avaliacao__atribuicao__disciplina', 'avaliacao__atribuicao__professor__user')
        .order_by('-avaliacao__validado_em', '-criado_em')[:8]
    )
    ultimas_notas = [
        {
            'disciplina': nota.avaliacao.atribuicao.disciplina,
            'professor': nota.avaliacao.atribuicao.professor,
            'nota': nota.mt,
            'aprovado': nota.mt >= MEDIA_MINIMA,
        }
        for nota in notas_recentes
    ]

    evolucao_labels = ['1º Trimestre', '2º Trimestre', '3º Trimestre']
    evolucao_dados = [
        _media(float(r.mt1) for r in resultados if r.mt1 and r.mt1 > 0) or 0,
        _media(float(r.mt2) for r in resultados if r.mt2 and r.mt2 > 0) or 0,
        _media(float(r.mt3) for r in resultados if r.mt3 and r.mt3 > 0) or 0,
    ]

    pautas_recentes = [
        {
            'disciplina': resultado.disciplina,
            'mf': resultado.mf,
            'frequencia': _frequencia_por_disciplina(aluno, resultado.disciplina),
        }
        for resultado in resultados
    ]

    periodo_atual, avaliacoes_periodo = _avaliacoes_periodo_atual(aluno)

    return {
        'resultados': resultados,
        'media_geral': media_geral,
        'frequencia': frequencia,
        'faltas': faltas,
        'mensagens': mensagens,
        'grafico_disciplinas_labels': [r.disciplina.nome for r in resultados],
        'grafico_mt1': [float(r.mt1) for r in resultados],
        'grafico_mt2': [float(r.mt2) for r in resultados],
        'grafico_mt3': [float(r.mt3) for r in resultados],
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
