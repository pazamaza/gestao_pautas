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
        'NPP',
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
            nota.npp,
            nota.npt,
            nota.mt,
            situacao_por_media(nota.mt),
            nota.observacao or '',
        ])

    tabela = Table(
        dados,
        repeatRows=1,
        colWidths=[28, 78, 180, 48, 48, 48, 48, 72, 180],
    )
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d9eaf7')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (1, -1), 'CENTER'),
        ('ALIGN', (3, 1), (7, -1), 'CENTER'),
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
