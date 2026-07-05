from decimal import Decimal

from pautas.models import ResultadoDisciplina

MEDIA_BOA = Decimal('14')
MEDIA_MINIMA = Decimal('10')
FREQUENCIA_MINIMA = 75
FREQUENCIA_BOA = 95


def estatisticas_aluno(aluno):
    resultados = (
        ResultadoDisciplina.objects
        .filter(aluno=aluno, status=ResultadoDisciplina.STATUS_VALIDADA)
        .select_related('disciplina')
        .order_by('disciplina__nome')
    )

    frequencia = aluno.calcular_frequencia()
    faltas = aluno.total_faltas()

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
    }
