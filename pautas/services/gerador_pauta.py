from pautas.models import Nota, LinhaPauta


def gerar_pauta(pauta):

    notas = Nota.objects.filter(
        avaliacao__atribuicao=pauta.atribuicao,
        avaliacao__periodo=pauta.periodo
    )

    for nota in notas:

        LinhaPauta.objects.update_or_create(

            pauta=pauta,

            aluno=nota.aluno,

            defaults={

                'media': nota.mt,

                'aprovado': nota.mt >= 10

            }
        )