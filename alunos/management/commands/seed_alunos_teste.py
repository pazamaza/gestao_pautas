import datetime
import itertools

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction

from alunos.models import Aluno, Encarregado
from turmas.models import Turma

PRIMEIROS_NOMES = [
    'Miguel', 'Ana', 'José', 'Fernanda', 'Domingos', 'Isabel', 'Manuel',
    'Luísa', 'Paulo', 'Teresa', 'Joana', 'Ricardo', 'Beatriz', 'Eduardo',
    'Marta', 'Francisco', 'Rita', 'Alberto', 'Sofia', 'Nelson', 'Vitória',
]

APELIDOS = [
    'Cabinda', 'Neto', 'Kamati', 'Sousa', 'Ferreira', 'Pinto', 'Baptista',
    'Chiconde', 'Zola', 'Kassoma', 'Lopes', 'Tavares', 'Cachinda', 'Muteka',
]

PROFISSOES = [
    'Comerciante', 'Motorista', 'Enfermeiro(a)', 'Empresário(a)',
    'Funcionário(a) Público(a)', 'Professor(a)',
]

# ano aproximado de nascimento por classe (idade típica em Angola)
ANO_NASCIMENTO_POR_CLASSE = {
    '7': 2013,
    '8': 2012,
    '9': 2011,
}


class Command(BaseCommand):
    help = (
        'Cria alunos e encarregados fictícios (dados de teste/exemplo) nas turmas '
        'de 7ª/8ª/9ª classe que ainda não têm nenhum aluno matriculado.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--por-turma', type=int, default=3,
            help='Número de alunos fictícios a criar por turma vazia (padrão: 3).'
        )

    def handle(self, *args, **options):
        por_turma = options['por_turma']

        turmas_vazias = [
            turma for turma in Turma.objects.filter(
                classe__nome__in=['7ª Classe', '8ª Classe', '9ª Classe']
            ).select_related('classe', 'ano_letivo')
            if not Aluno.objects.filter(turma=turma).exists()
        ]

        if not turmas_vazias:
            self.stdout.write('Nenhuma turma vazia encontrada — nada a fazer.')
            return

        nomes = itertools.cycle(itertools.product(PRIMEIROS_NOMES, APELIDOS))
        profissoes = itertools.cycle(PROFISSOES)
        telefone_seq = itertools.count(900000001)

        total_criados = 0
        grupo_encarregado, _ = Group.objects.get_or_create(name='Encarregado')

        with transaction.atomic():
            for turma in turmas_vazias:
                classe_digito = turma.classe.nome[0]
                ano_nascimento = ANO_NASCIMENTO_POR_CLASSE.get(classe_digito, 2012)

                for indice in range(1, por_turma + 1):
                    primeiro, ultimo = next(nomes)
                    nome_completo = f'{primeiro} {ultimo}'
                    numero_processo = f'{turma.ano_letivo.descricao}-{classe_digito}{turma.nome}-{indice:02d}'

                    username_enc = f"enc_{numero_processo.lower().replace('-', '_')}"
                    user_enc = User.objects.create_user(
                        username=username_enc,
                        password='mudar@123',
                        first_name=f'Encarregado de {primeiro}',
                        last_name=ultimo,
                    )
                    user_enc.groups.add(grupo_encarregado)
                    encarregado = Encarregado.objects.create(
                        user=user_enc,
                        telefone=str(next(telefone_seq)),
                        profissao=next(profissoes),
                    )

                    Aluno.objects.create(
                        nome=nome_completo,
                        numero_processo=numero_processo,
                        data_nascimento=datetime.date(ano_nascimento, (indice % 12) + 1, (indice % 27) + 1),
                        sexo='M' if indice % 2 else 'F',
                        turma=turma,
                        encarregado=encarregado,
                        estado=Aluno.ESTADO_ATIVO,
                    )
                    total_criados += 1

                self.stdout.write(
                    f'{turma.classe.nome} {turma.nome} ({turma.ano_letivo}): '
                    f'{por_turma} aluno(s) criado(s).'
                )

        self.stdout.write(self.style.SUCCESS(
            f'\nConcluído: {total_criados} aluno(s) de teste criado(s) em '
            f'{len(turmas_vazias)} turma(s). Password dos encarregados criados: "mudar@123" '
            '(dados fictícios — trocar/remover antes de produção).'
        ))
