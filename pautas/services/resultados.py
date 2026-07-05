from decimal import Decimal

from alunos.models import Aluno
from pautas.models import Nota, ResultadoDisciplina


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


def gerar_resultados_finais():
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
