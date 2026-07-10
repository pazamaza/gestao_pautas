from io import BytesIO

from pautas.services.excel import situacao_por_media


def exportar_pauta_pdf(avaliacao, notas):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    output = BytesIO()
    documento = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24,
        title='Pauta Trimestral',
    )

    estilos = getSampleStyleSheet()
    elementos = [
        Paragraph('Gestao de Pautas', estilos['Title']),
        Paragraph('Pauta Trimestral', estilos['Heading2']),
        Paragraph(str(avaliacao.atribuicao), estilos['Normal']),
        Paragraph(str(avaliacao.periodo), estilos['Normal']),
        Spacer(1, 14),
    ]

    dados = [[
        'Nº',
        'Nº Processo',
        'Aluno',
        'MAC',
        'NPT',
        'MT',
        'Situacao',
        'Observacao',
    ]]

    for indice, nota in enumerate(notas, start=1):
        dados.append([
            indice,
            nota.aluno.numero_processo,
            nota.aluno.nome,
            nota.mac,
            nota.npt,
            nota.mt,
            situacao_por_media(nota.mt),
            nota.observacao or '',
        ])

    tabela = Table(
        dados,
        repeatRows=1,
        colWidths=[28, 78, 180, 48, 48, 48, 72, 180],
    )
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d9eaf7')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (1, -1), 'CENTER'),
        ('ALIGN', (3, 1), (6, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f7f7')]),
    ]))

    elementos.append(tabela)
    documento.build(elementos)
    output.seek(0)
    return output


def exportar_mini_pauta_pdf(turma, disciplina, ano_letivo, linhas):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    output = BytesIO()
    documento = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24,
        title='Mini-Pauta Trimestral',
    )

    estilos = getSampleStyleSheet()
    elementos = [
        Paragraph('Gestao de Pautas', estilos['Title']),
        Paragraph(f'Mini-Pauta - {disciplina}', estilos['Heading2']),
        Paragraph(
            f'Turma: {turma} | Sala: {turma.sala or "-"} | Ano Letivo: {ano_letivo}',
            estilos['Normal'],
        ),
        Spacer(1, 10),
    ]

    linha_trimestres = ['Nº', 'Aluno', 'Faltas']
    linha_subcabecalhos = ['', '', '']
    for nome_trimestre in ('I Trimestre', 'II Trimestre', 'III Trimestre'):
        linha_trimestres.extend([nome_trimestre, '', ''])
        linha_subcabecalhos.extend(['MAC', 'NPT', 'MT'])
    linha_trimestres.append('MFD')
    linha_subcabecalhos.append('')

    dados = [linha_trimestres, linha_subcabecalhos]

    for indice, linha in enumerate(linhas, start=1):
        valores = [indice, str(linha['aluno']), linha['faltas']]
        for campo in ('mt1', 'mt2', 'mt3'):
            nota = linha[campo]
            if nota:
                valores.extend([nota.mac, nota.npt, nota.mt])
            else:
                valores.extend(['-', '-', '-'])
        resultado = linha['resultado']
        valores.append(resultado.mf if resultado else '-')
        dados.append(valores)

    col_widths = [24, 130, 40] + [34] * 9 + [40]
    ultima_coluna = len(linha_trimestres) - 1

    estilo_tabela = [
        ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor('#d9eaf7')),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('SPAN', (0, 0), (0, 1)),
        ('SPAN', (1, 0), (1, 1)),
        ('SPAN', (2, 0), (2, 1)),
        ('SPAN', (ultima_coluna, 0), (ultima_coluna, 1)),
        ('ROWBACKGROUNDS', (0, 2), (-1, -1), [colors.white, colors.HexColor('#f7f7f7')]),
    ]

    coluna = 3
    for _ in range(3):
        estilo_tabela.append(('SPAN', (coluna, 0), (coluna + 2, 0)))
        coluna += 3

    tabela = Table(dados, repeatRows=2, colWidths=col_widths)
    tabela.setStyle(TableStyle(estilo_tabela))

    elementos.append(tabela)
    documento.build(elementos)
    output.seek(0)
    return output


def exportar_pauta_final_pdf(turma, ano_letivo, disciplinas, linhas):
    from core.models import Escola
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    output = BytesIO()
    documento = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=18,
        leftMargin=18,
        topMargin=18,
        bottomMargin=18,
        title='Pauta Final da Turma',
    )

    escola = Escola.obter_configuracao()
    estilos = getSampleStyleSheet()
    elementos = []

    if escola:
        for texto in (escola.ministerio, escola.governo_provincial, escola.administracao_municipal):
            if texto:
                elementos.append(Paragraph(texto, estilos['Normal']))
        elementos.append(Paragraph(escola.nome, estilos['Title']))
        if turma.numero_pauta:
            elementos.append(Paragraph(f'PAUTA Nº {turma.numero_pauta}', estilos['Heading3']))
    else:
        elementos.append(Paragraph('Gestao de Pautas', estilos['Title']))

    elementos.append(Paragraph(f'Pauta Final - {turma}', estilos['Heading2']))
    elementos.append(
        Paragraph(
            f'Sala: {turma.sala or "-"} | Periodo: {turma.get_periodo_display() or "-"} | '
            f'Ano Letivo: {ano_letivo}',
            estilos['Normal'],
        )
    )
    elementos.append(Spacer(1, 10))

    linha_disciplinas = ['Nº', 'Aluno']
    linha_subcabecalhos = ['', '']
    for disciplina in disciplinas:
        linha_disciplinas.extend([str(disciplina), '', '', ''])
        linha_subcabecalhos.extend(['MFD', 'NE', 'MF', 'NER'])
    linha_disciplinas.append('Situação Geral')
    linha_subcabecalhos.append('')

    dados = [linha_disciplinas, linha_subcabecalhos]

    for indice, linha in enumerate(linhas, start=1):
        valores = [indice, str(linha['aluno'])]
        for resultado in linha['celulas']:
            if resultado:
                valores.extend([
                    resultado.mf,
                    resultado.exame if resultado.exame is not None else '-',
                    resultado.nota_final if resultado.nota_final is not None else '-',
                    resultado.nota_recurso if resultado.nota_recurso is not None else '-',
                ])
            else:
                valores.extend(['-', '-', '-', '-'])
        situacao_anual = linha['situacao_anual']
        valores.append(situacao_anual.situacao if situacao_anual else '-')
        dados.append(valores)

    colunas_notas = len(disciplinas) * 4
    col_widths = [24, 110] + [32] * colunas_notas + [90]

    ultima_coluna = len(linha_disciplinas) - 1
    estilo_tabela = [
        ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor('#d9eaf7')),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('SPAN', (0, 0), (0, 1)),
        ('SPAN', (1, 0), (1, 1)),
        ('SPAN', (ultima_coluna, 0), (ultima_coluna, 1)),
        ('ROWBACKGROUNDS', (0, 2), (-1, -1), [colors.white, colors.HexColor('#f7f7f7')]),
    ]

    coluna = 2
    for _ in disciplinas:
        estilo_tabela.append(('SPAN', (coluna, 0), (coluna + 3, 0)))
        coluna += 4

    tabela = Table(dados, repeatRows=2, colWidths=col_widths)
    tabela.setStyle(TableStyle(estilo_tabela))

    elementos.append(tabela)

    if escola and escola.nome_autoridade_visto:
        elementos.append(Spacer(1, 24))
        elementos.append(Paragraph(f'VISTO DA {escola.cargo_autoridade_visto.upper()}', estilos['Normal']))
        elementos.append(Paragraph(escola.nome_autoridade_visto, estilos['Normal']))

    documento.build(elementos)
    output.seek(0)
    return output
