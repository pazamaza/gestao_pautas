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
    from django.contrib.staticfiles import finders
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A3, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    # A pauta final tem 4 colunas de notas por disciplina — com muitas
    # disciplinas isso facilmente ultrapassa a largura de uma A4 paisagem
    # (a tabela ficava cortada/incompleta). A3 paisagem dá quase o dobro do
    # espaço; as larguras de coluna abaixo são também calculadas para caber
    # sempre na página, em vez de uma largura fixa que podia transbordar.
    output = BytesIO()
    documento = SimpleDocTemplate(
        output,
        pagesize=landscape(A3),
        rightMargin=18,
        leftMargin=18,
        topMargin=18,
        bottomMargin=18,
        title='Pauta Final da Turma',
    )

    escola = Escola.obter_configuracao()
    estilos = getSampleStyleSheet()
    # Cabeçalho institucional da pauta geral — todas as linhas centradas e a
    # negrito, replicando o modelo oficial (República/Ministério/Governo
    # Provincial/Administração Municipal/Escola/Pauta Nº/Ano Lectivo).
    estilo_cabecalho = ParagraphStyle(
        'CabecalhoInstitucional', parent=estilos['Normal'],
        fontName='Helvetica-Bold', fontSize=11, leading=13, alignment=1,
    )
    estilo_escola = ParagraphStyle('NomeEscola', parent=estilo_cabecalho, fontSize=13)
    elementos = []

    caminho_insignia = finders.find('images/insignia_angola.png')
    if caminho_insignia:
        insignia = Image(caminho_insignia, width=45, height=50)
        insignia.hAlign = 'CENTER'
        elementos.append(insignia)
        elementos.append(Spacer(1, 4))

    elementos.append(Paragraph('REPÚBLICA DE ANGOLA', estilo_cabecalho))
    if escola:
        for texto in (escola.ministerio, escola.governo_provincial, escola.administracao_municipal):
            if texto:
                elementos.append(Paragraph(texto, estilo_cabecalho))
        elementos.append(Paragraph(escola.nome, estilo_escola))
        if turma.numero_pauta:
            elementos.append(Paragraph(f'PAUTA Nº {turma.numero_pauta}', estilo_cabecalho))
    else:
        elementos.append(Paragraph('Gestao de Pautas', estilo_escola))

    # Classes EJA usam só o numeral ordinal ("Iº"/"IIº") — no cabeçalho
    # impresso isso deve ler-se por extenso ("IIº Ano").
    classe_texto = str(turma.classe)
    if classe_texto.endswith('º'):
        classe_texto = f'{classe_texto} Ano'

    elementos.append(Spacer(1, 4))
    elementos.append(
        Paragraph(
            f'ANO LECTIVO: {ano_letivo} &nbsp;&nbsp;&nbsp;&nbsp; {classe_texto} &nbsp;&nbsp;&nbsp;&nbsp; '
            f'TURMA: {turma.nome} &nbsp;&nbsp;&nbsp;&nbsp; SALA: {turma.sala or "-"}',
            estilo_cabecalho,
        )
    )
    elementos.append(Spacer(1, 10))

    # "Aprovado por Compensação" (e a Observação) não cabem numa linha com
    # texto simples (que não quebra linha em Tables do reportlab) — por
    # isso usa-se Paragraph, que quebra automaticamente.
    estilo_situacao = ParagraphStyle(
        'SituacaoGeral', parent=estilos['Normal'], fontSize=6.5, leading=8, alignment=1,
    )
    estilo_observacao = ParagraphStyle(
        'Observacao', parent=estilos['Normal'], fontSize=6, leading=7.5, alignment=0,
    )

    segundo_ano = turma.eh_segundo_ano()
    rotulos_disciplina = (
        ['M1ºT', 'M2ºT', 'M3ºT', 'MFA', 'NER'] if segundo_ano else ['M1ºT', 'M2ºT', 'M3ºT', 'MFD']
    )
    n_cols_disciplina = len(rotulos_disciplina)

    linha_disciplinas = ['Nº', 'Aluno']
    linha_subcabecalhos = ['', '']
    for disciplina in disciplinas:
        linha_disciplinas.extend([str(disciplina)] + [''] * (n_cols_disciplina - 1))
        linha_subcabecalhos.extend(rotulos_disciplina)
    linha_disciplinas.extend(['Situação Geral', 'Observação'])
    linha_subcabecalhos.extend(['', ''])

    dados = [linha_disciplinas, linha_subcabecalhos]
    # (linha_na_tabela, coluna) das células MFD/MFA, para colorir a
    # azul/vermelho consoante aprovação.
    celulas_mfd = []

    for indice, linha in enumerate(linhas, start=1):
        valores = [indice, str(linha['aluno'])]
        coluna_atual = 2
        for resultado in linha['celulas']:
            if resultado:
                valores.extend([resultado.mt1, resultado.mt2, resultado.mt3, resultado.mf])
                celulas_mfd.append((len(dados), coluna_atual + 3, resultado.mf >= 10))
                if segundo_ano:
                    valores.append(resultado.nota_recurso if resultado.nota_recurso is not None else '-')
            else:
                valores.extend(['-'] * n_cols_disciplina)
            coluna_atual += n_cols_disciplina
        situacao_anual = linha['situacao_anual']
        if situacao_anual:
            texto_situacao = situacao_anual.situacao
        elif linha.get('aguarda_recurso'):
            texto_situacao = 'Recurso'
        else:
            texto_situacao = '-'
        valores.append(Paragraph(texto_situacao, estilo_situacao))
        valores.append(Paragraph(linha.get('observacao') or '-', estilo_observacao))
        dados.append(valores)

    # Larguras calculadas para caber sempre na página (em vez de uma largura
    # fixa por coluna, que com muitas disciplinas ultrapassava a página e
    # cortava a pauta) — ver comentário acima sobre o motivo de usar A3.
    largura_pagina, _altura_pagina = landscape(A3)
    largura_util = largura_pagina - 36  # margens esquerda+direita
    col_no, col_aluno, col_situacao, col_observacao = 20, 85, 65, 90
    colunas_notas = len(disciplinas) * n_cols_disciplina
    largura_disponivel_notas = largura_util - col_no - col_aluno - col_situacao - col_observacao
    col_dado = (largura_disponivel_notas / colunas_notas) if colunas_notas else 0
    col_dado = max(14, min(32, col_dado))
    col_widths = [col_no, col_aluno] + [col_dado] * colunas_notas + [col_situacao, col_observacao]
    tamanho_fonte = 7 if col_dado >= 20 else (6 if col_dado >= 16 else 5)

    ultima_coluna = len(linha_disciplinas) - 1
    coluna_situacao = ultima_coluna - 1
    estilo_tabela = [
        ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor('#d9eaf7')),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), tamanho_fonte),
        ('SPAN', (0, 0), (0, 1)),
        ('SPAN', (1, 0), (1, 1)),
        ('SPAN', (coluna_situacao, 0), (coluna_situacao, 1)),
        ('SPAN', (ultima_coluna, 0), (ultima_coluna, 1)),
        ('ROWBACKGROUNDS', (0, 2), (-1, -1), [colors.white, colors.HexColor('#f7f7f7')]),
    ]

    coluna = 2
    for _ in disciplinas:
        estilo_tabela.append(('SPAN', (coluna, 0), (coluna + n_cols_disciplina - 1, 0)))
        coluna += n_cols_disciplina

    for linha_tabela, coluna_mfd, aprovado in celulas_mfd:
        cor = colors.HexColor('#0d6efd') if aprovado else colors.HexColor('#dc3545')
        estilo_tabela.append(('TEXTCOLOR', (coluna_mfd, linha_tabela), (coluna_mfd, linha_tabela), cor))
        estilo_tabela.append(('FONTNAME', (coluna_mfd, linha_tabela), (coluna_mfd, linha_tabela), 'Helvetica-Bold'))

    tabela = Table(dados, repeatRows=2, colWidths=col_widths)
    tabela.setStyle(TableStyle(estilo_tabela))

    elementos.append(tabela)

    elementos.append(Spacer(1, 24))
    estilo_rodape_esquerda = ParagraphStyle(
        'RodapeConselho', parent=estilos['Normal'], fontName='Helvetica-Bold', fontSize=10, alignment=0,
    )
    estilo_rodape_direita = ParagraphStyle(
        'RodapeLocalidade', parent=estilos['Normal'], fontName='Helvetica-Bold', fontSize=10, alignment=2,
    )
    estilo_assinatura_titulo = ParagraphStyle(
        'AssinaturaTitulo', parent=estilos['Normal'], fontName='Helvetica-Bold', fontSize=9, alignment=1,
    )
    estilo_assinatura_nome = ParagraphStyle(
        'AssinaturaNome', parent=estilos['Normal'], fontSize=9, alignment=1,
    )

    localidade = escola.localidade.upper() if escola and escola.localidade else '_______________'
    linha_localidade_data = f'{localidade}, ______ / ______ / __________'

    cabecalho_rodape = Table(
        [[
            Paragraph('O CONSELHO DE NOTAS', estilo_rodape_esquerda),
            Paragraph(linha_localidade_data, estilo_rodape_direita),
        ]],
        colWidths=[largura_util * 0.5, largura_util * 0.5],
    )
    cabecalho_rodape.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'BOTTOM')]))
    elementos.append(cabecalho_rodape)
    elementos.append(Spacer(1, 16))

    linha_assinatura = '_' * 35
    nome_subdirector = escola.nome_subdirector_pedagogico if escola else ''
    nome_diretor = escola.nome_autoridade_visto if escola else ''

    dados_assinaturas = [
        [
            f'1. {linha_assinatura}',
            Paragraph('O SUBDIRECTOR PEDAGÓGICO', estilo_assinatura_titulo),
            Paragraph('O DIRECTOR DO COMPLEXO ESCOLAR', estilo_assinatura_titulo),
        ],
        [f'2. {linha_assinatura}', linha_assinatura, linha_assinatura],
        [
            f'3. {linha_assinatura}',
            Paragraph(nome_subdirector, estilo_assinatura_nome),
            Paragraph(nome_diretor, estilo_assinatura_nome),
        ],
    ]
    tabela_assinaturas = Table(
        dados_assinaturas,
        colWidths=[largura_util * 0.4, largura_util * 0.3, largura_util * 0.3],
    )
    tabela_assinaturas.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elementos.append(tabela_assinaturas)

    documento.build(elementos)
    output.seek(0)
    return output


def _cabecalho_escola(elementos, estilos, escola):
    from reportlab.platypus import Paragraph

    if escola:
        for texto in (escola.ministerio, escola.governo_provincial, escola.administracao_municipal):
            if texto:
                elementos.append(Paragraph(texto, estilos['Normal']))
        elementos.append(Paragraph(escola.nome, estilos['Title']))
    else:
        elementos.append(Paragraph('Gestao de Pautas', estilos['Title']))


def exportar_boletim_pdf(aluno, ano_letivo, resultados):
    from core.models import Escola
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    output = BytesIO()
    documento = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
        title='Boletim de Notas',
    )

    escola = Escola.obter_configuracao()
    estilos = getSampleStyleSheet()
    elementos = []
    _cabecalho_escola(elementos, estilos, escola)

    elementos.append(Paragraph('Boletim de Notas', estilos['Heading2']))
    elementos.append(
        Paragraph(
            f'Aluno: {aluno.nome} | Nº Processo: {aluno.numero_processo}',
            estilos['Normal'],
        )
    )
    elementos.append(
        Paragraph(
            f'Turma: {aluno.turma} | Ano Letivo: {ano_letivo}',
            estilos['Normal'],
        )
    )
    elementos.append(Spacer(1, 14))

    dados = [['Disciplina', '1º Trimestre', '2º Trimestre', '3º Trimestre', 'Média Final', 'Situação']]
    for resultado in resultados:
        dados.append([
            resultado.disciplina.nome,
            resultado.mt1 if resultado.mt1 else '-',
            resultado.mt2 if resultado.mt2 else '-',
            resultado.mt3 if resultado.mt3 else '-',
            resultado.mf if resultado.mf else '-',
            resultado.resultado or '-',
        ])

    tabela = Table(dados, repeatRows=1, colWidths=[160, 70, 70, 70, 70, 80])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d9eaf7')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f7f7')]),
    ]))
    elementos.append(tabela)

    elementos.append(Spacer(1, 24))
    elementos.append(Paragraph(
        f'Documento emitido automaticamente pelo sistema de gestão de pautas.',
        estilos['Normal'],
    ))

    documento.build(elementos)
    output.seek(0)
    return output


def exportar_declaracao_pdf(aluno, ano_letivo, resultados):
    from core.models import Escola
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    output = BytesIO()
    documento = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
        title='Declaração de Notas',
    )

    escola = Escola.obter_configuracao()
    estilos = getSampleStyleSheet()
    elementos = []
    _cabecalho_escola(elementos, estilos, escola)

    elementos.append(Paragraph('Declaração de Notas', estilos['Heading2']))
    elementos.append(
        Paragraph(
            f'Declara-se, para os devidos efeitos, que {aluno.nome} '
            f'(Nº Processo: {aluno.numero_processo}), aluno(a) da turma '
            f'{aluno.turma}, obteve no ano letivo {ano_letivo} os seguintes '
            'resultados:',
            estilos['Normal'],
        )
    )
    elementos.append(Spacer(1, 14))

    dados = [['Disciplina', '1º Trimestre', '2º Trimestre', '3º Trimestre', 'Média Final', 'Situação']]
    for resultado in resultados:
        dados.append([
            resultado.disciplina.nome,
            resultado.mt1 if resultado.mt1 else '-',
            resultado.mt2 if resultado.mt2 else '-',
            resultado.mt3 if resultado.mt3 else '-',
            resultado.mf if resultado.mf else '-',
            resultado.resultado or '-',
        ])

    tabela = Table(dados, repeatRows=1, colWidths=[160, 70, 70, 70, 70, 80])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d9eaf7')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f7f7')]),
    ]))
    elementos.append(tabela)

    elementos.append(Spacer(1, 24))
    elementos.append(Paragraph(
        'Documento emitido automaticamente pelo sistema de gestão de pautas.',
        estilos['Normal'],
    ))

    documento.build(elementos)
    output.seek(0)
    return output


_VALORES_POR_EXTENSO = {
    0: 'Zero', 1: 'Um', 2: 'Dois', 3: 'Três', 4: 'Quatro', 5: 'Cinco',
    6: 'Seis', 7: 'Sete', 8: 'Oito', 9: 'Nove', 10: 'Dez', 11: 'Onze',
    12: 'Doze', 13: 'Treze', 14: 'Catorze', 15: 'Quinze', 16: 'Dezasseis',
    17: 'Dezassete', 18: 'Dezoito', 19: 'Dezanove', 20: 'Vinte',
}


def _valor_por_extenso(valor):
    if valor is None:
        return None
    return _VALORES_POR_EXTENSO.get(int(valor), str(valor))


def _data_por_extenso(data):
    from django.utils.formats import date_format

    if not data:
        return '-'
    return date_format(data, format='j \\d\\e F \\d\\e Y')


def exportar_certificado_pdf(aluno, turma, ano_letivo, resultados):
    from decimal import ROUND_HALF_UP, Decimal

    from core.models import Escola
    from django.contrib.staticfiles import finders
    from django.utils import timezone
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    output = BytesIO()
    documento = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=48,
        leftMargin=48,
        topMargin=40,
        bottomMargin=40,
        title='Certificado',
    )

    escola = Escola.obter_configuracao()
    estilos = getSampleStyleSheet()
    estilo_cabecalho = ParagraphStyle(
        'CabecalhoCertificado', parent=estilos['Normal'],
        fontName='Helvetica-Bold', fontSize=12, leading=15, alignment=1,
    )
    estilo_titulo = ParagraphStyle(
        'TituloCertificado', parent=estilo_cabecalho, fontSize=13, spaceBefore=8,
    )
    estilo_corpo = ParagraphStyle(
        'CorpoCertificado', parent=estilos['Normal'], fontSize=10.5, leading=16,
        alignment=TA_JUSTIFY,
    )
    estilo_assinatura = ParagraphStyle(
        'AssinaturaCertificado', parent=estilos['Normal'], fontSize=9.5, alignment=1,
    )
    elementos = []

    caminho_insignia = finders.find('images/insignia_angola.png')
    if caminho_insignia:
        insignia = Image(caminho_insignia, width=50, height=55)
        insignia.hAlign = 'CENTER'
        elementos.append(insignia)
        elementos.append(Spacer(1, 4))

    elementos.append(Paragraph('REPÚBLICA DE ANGOLA', estilo_cabecalho))
    elementos.append(Paragraph(escola.ministerio if escola else 'Ministério da Educação', estilo_cabecalho))
    elementos.append(Spacer(1, 10))

    # EJA Iº/IIº Ano — o "ciclo" do certificado corresponde à classe da
    # turma no momento da conclusão (ver Turma.eh_segundo_ano()).
    titulo_ciclo = f'{turma.classe} CICLO DO ENSINO SECUNDÁRIO'
    elementos.append(Paragraph(titulo_ciclo, estilo_titulo))
    elementos.append(Paragraph('CERTIFICADO', estilo_titulo))
    elementos.append(Spacer(1, 16))

    nome_diretor = escola.nome_autoridade_visto if escola else ''
    cargo_diretor = (escola.cargo_autoridade_visto if escola and escola.cargo_autoridade_visto
                      else 'Director do Complexo Escolar')
    nome_escola = escola.nome if escola else 'Gestão de Pautas'
    decreto = escola.decreto_criacao if escola else ''
    base_legal = escola.base_legal_certificado if escola else ''
    livro_registo = escola.livro_registo_certificado if escola else ''
    provincia = escola.provincia if escola else ''

    resultados = list(resultados)
    valores_mf = [r.mf for r in resultados if r.mf is not None]
    media_geral = None
    if valores_mf:
        media_geral = (sum(valores_mf, Decimal('0')) / len(valores_mf)).quantize(
            Decimal('1'), rounding=ROUND_HALF_UP
        )

    filiacao = f'{aluno.nome_pai} e de {aluno.nome_mae}' if aluno.nome_pai else f'{aluno.nome_mae or "-"}'
    texto = (
        f'<b>{nome_diretor}</b>, {cargo_diretor}, certifica que <b>{aluno.nome}</b>, filho(a) de '
        f'{filiacao}, natural de {aluno.naturalidade or "-"}, Município de '
        f'{aluno.municipio_natural or "-"}, Província de {aluno.provincia_natal or "-"}, nascido(a) aos '
        f'{_data_por_extenso(aluno.data_nascimento)}, portador(a) do B.I. nº {aluno.numero_bi or "-"}, '
        f'passado {aluno.local_emissao_bi or "-"} aos {_data_por_extenso(aluno.data_emissao_bi)}, '
        f'concluiu no {nome_escola}'
        + (f', criado sob decreto nº {decreto}' if decreto else '')
        + f', no ano lectivo {ano_letivo} o {titulo_ciclo}'
        + (f', conforme o disposto na {base_legal}' if base_legal else '')
        + (f', com a média de {media_geral} Valores' if media_geral is not None else '')
        + ' obtida nas seguintes classificações por trimestre de aprendizagem:'
    )
    elementos.append(Paragraph(texto, estilo_corpo))
    elementos.append(Spacer(1, 16))

    dados = [['Disciplina', 'Média 1º T', 'Média 2º T', 'Média 3º T', 'Média Final', 'Média por Extenso']]
    for resultado in resultados:
        extenso = _valor_por_extenso(resultado.mf)
        dados.append([
            resultado.disciplina.nome,
            resultado.mt1 if resultado.mt1 is not None else '-',
            resultado.mt2 if resultado.mt2 is not None else '-',
            resultado.mt3 if resultado.mt3 is not None else '-',
            resultado.mf if resultado.mf is not None else '-',
            f'{extenso} Valores' if extenso else '-',
        ])

    tabela = Table(dados, repeatRows=1, colWidths=[145, 52, 52, 52, 58, 130])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d9eaf7')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f7f7')]),
    ]))
    elementos.append(tabela)
    elementos.append(Spacer(1, 16))

    elementos.append(Paragraph(
        'Para efeitos legais lhe é passado o presente Certificado'
        + (f', que consta no livro de registo {livro_registo}' if livro_registo else '')
        + ', assinado por mim e autenticado com carimbo a óleo/selo branco em uso neste '
        'estabelecimento de ensino.',
        estilo_corpo,
    ))
    elementos.append(Spacer(1, 10))
    elementos.append(Paragraph(
        f'{nome_escola}{f" em {provincia}" if provincia else ""}, aos '
        f'{_data_por_extenso(timezone.localdate())}.',
        estilo_corpo,
    ))
    elementos.append(Spacer(1, 40))

    linha_assinatura = '_' * 30
    tabela_assinaturas = Table(
        [
            ['Confirido por', f'O {cargo_diretor}'],
            [linha_assinatura, linha_assinatura],
            ['', nome_diretor],
        ],
        colWidths=[220, 220],
    )
    tabela_assinaturas.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elementos.append(tabela_assinaturas)

    documento.build(elementos)
    output.seek(0)
    return output
