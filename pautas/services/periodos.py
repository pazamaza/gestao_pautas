NOMES_PERIODOS = {
    'Iº Trimestre': 'mt1',
    '1º Trimestre': 'mt1',
    'I Trimestre': 'mt1',
    'IIº Trimestre': 'mt2',
    '2º Trimestre': 'mt2',
    'II Trimestre': 'mt2',
    'IIIº Trimestre': 'mt3',
    '3º Trimestre': 'mt3',
    'III Trimestre': 'mt3',
}


def campo_periodo(periodo):
    nome = periodo.nome.strip()
    return NOMES_PERIODOS.get(nome)
