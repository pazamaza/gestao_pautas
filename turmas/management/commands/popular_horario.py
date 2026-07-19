from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from professores.models import AtribuicaoDocente
from turmas.models import AnoLetivo, HorarioAula, Turma

# Código interno -> id da Disciplina já cadastrada (ver disciplinas/models.py).
DISCIPLINA_IDS = {
    'LPOR': 1,   # L. Port
    'LING': 2,   # L. Ingl
    'FIS': 3,    # Física
    'ELAB': 4,   # Ed. Lab.
    'BIO': 5,    # Biol.
    'QUI': 6,    # Química
    'MAT': 7,    # Matm.
    'EVP': 8,    # E. V. P.
    'HIST': 9,   # História
    'GEO': 10,   # Geogr
    'EMC': 11,   # E. M. C.
    'EMP': 12,   # Empr
}

# Rótulo da turma no papel -> (nome da Classe, nome da Turma) já cadastrados.
TURMAS = {
    '1A': ('Iº', 'AN'),
    '1B': ('Iº', 'BN'),
    '1C': ('Iº', 'CN'),
    '2A': ('IIº', 'AN'),
    '2B': ('IIº', 'BN'),
    '2C': ('IIº', 'CN'),
}

# GRELHA[dia][turma] = lista de 6 códigos de disciplina (tempos 1 a 6).
# None representa "Borla" (tempo livre), conforme as imagens da pasta Horários/.
GRELHA = {
    HorarioAula.SEGUNDA: {
        '1A': ['HIST', 'HIST', 'EMC', None, 'LPOR', 'LPOR'],
        '1B': ['LPOR', 'LPOR', 'HIST', 'HIST', 'EMC', None],
        '1C': ['EMC', None, 'LPOR', 'LPOR', 'HIST', 'HIST'],
        '2A': ['BIO', 'BIO', 'EMP', 'EMP', 'GEO', 'EMC'],
        '2B': ['GEO', 'EMC', 'BIO', 'BIO', 'EMP', 'EMP'],
        '2C': ['EMP', 'EMP', 'GEO', 'EMC', 'BIO', 'BIO'],
    },
    HorarioAula.TERCA: {
        '1A': ['MAT', 'MAT', 'BIO', 'BIO', 'LING', 'LING'],
        '1B': ['LING', 'LING', 'MAT', 'MAT', 'BIO', 'BIO'],
        '1C': ['BIO', 'BIO', 'LING', 'LING', 'MAT', 'MAT'],
        '2A': ['EVP', 'EVP', 'GEO', 'GEO', 'LPOR', 'LPOR'],
        '2B': ['LPOR', 'LPOR', 'EVP', 'EVP', 'GEO', 'GEO'],
        '2C': ['GEO', 'GEO', 'LPOR', 'LPOR', 'EVP', 'EVP'],
    },
    HorarioAula.QUARTA: {
        '1A': ['ELAB', 'ELAB', 'LING', 'FIS', 'LPOR', None],
        '1B': ['LPOR', 'FIS', 'ELAB', 'ELAB', None, 'LING'],
        '1C': [None, 'LPOR', 'FIS', 'LING', 'ELAB', 'ELAB'],
        '2A': ['HIST', 'HIST', 'BIO', 'LPOR', 'LING', 'QUI'],
        '2B': ['LING', 'BIO', 'LPOR', 'QUI', 'HIST', 'HIST'],
        '2C': ['BIO', 'LING', 'HIST', 'HIST', 'QUI', 'LPOR'],
    },
    HorarioAula.QUINTA: {
        '1A': ['QUI', 'QUI', 'EMP', 'EMP', 'HIST', 'MAT'],
        '1B': ['HIST', 'MAT', 'QUI', 'QUI', 'EMP', 'EMP'],
        '1C': ['EMP', 'EMP', 'HIST', 'MAT', 'QUI', 'QUI'],
        '2A': ['ELAB', 'ELAB', 'MAT', None, 'FIS', 'FIS'],
        '2B': ['FIS', 'FIS', 'ELAB', 'ELAB', 'MAT', None],
        '2C': ['MAT', None, 'FIS', 'FIS', 'ELAB', 'ELAB'],
    },
    HorarioAula.SEXTA: {
        '1A': ['GEO', 'GEO', 'FIS', 'FIS', 'EVP', 'EVP'],
        '1B': ['EVP', 'EVP', 'GEO', 'GEO', 'FIS', 'FIS'],
        '1C': ['FIS', 'FIS', 'EVP', 'EVP', 'GEO', 'GEO'],
        '2A': ['QUI', 'QUI', 'MAT', 'MAT', 'LING', 'LING'],
        '2B': ['LING', 'LING', 'QUI', 'QUI', 'MAT', 'MAT'],
        '2C': ['MAT', 'MAT', 'LING', 'LING', 'QUI', 'QUI'],
    },
}


class Command(BaseCommand):
    help = (
        'Popula o Horário Semanal de Aulas (HorarioAula) a partir da grelha '
        'transcrita das imagens da pasta "Horários/".'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--ano-letivo', type=str, default=None,
            help='Descrição exacta do Ano Letivo a usar (por omissão, o ano letivo activo).'
        )

    def handle(self, *args, **options):
        ano_letivo = self._obter_ano_letivo(options['ano_letivo'])
        self.stdout.write(f'Ano lectivo: {ano_letivo}')

        criados = 0
        atualizados = 0
        sem_atribuicao = []

        with transaction.atomic():
            for dia, turmas_do_dia in GRELHA.items():
                for turma_label, codigos in turmas_do_dia.items():
                    turma = self._obter_turma(turma_label, ano_letivo)
                    for tempo, codigo in enumerate(codigos, start=1):
                        atribuicao = None
                        if codigo is not None:
                            atribuicao = AtribuicaoDocente.objects.filter(
                                turma=turma,
                                disciplina_id=DISCIPLINA_IDS[codigo],
                                ano_letivo=ano_letivo,
                                ativo=True,
                            ).first()
                            if atribuicao is None:
                                sem_atribuicao.append((turma_label, dia, tempo, codigo))
                                continue

                        _, criado = HorarioAula.objects.update_or_create(
                            turma=turma, dia_semana=dia, tempo=tempo,
                            defaults={'atribuicao': atribuicao},
                        )
                        if criado:
                            criados += 1
                        else:
                            atualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'{criados} horário(s) criado(s), {atualizados} atualizado(s).'
        ))
        if sem_atribuicao:
            self.stdout.write(self.style.WARNING(
                f'{len(sem_atribuicao)} célula(s) sem AtribuicaoDocente correspondente (não gravadas):'
            ))
            for item in sem_atribuicao:
                self.stdout.write(f'  {item}')

    def _obter_ano_letivo(self, descricao):
        if descricao:
            try:
                return AnoLetivo.objects.get(descricao=descricao)
            except AnoLetivo.DoesNotExist:
                raise CommandError(f'Ano lectivo "{descricao}" não encontrado.')
        ano_letivo = AnoLetivo.objects.filter(ativo=True).first()
        if not ano_letivo:
            raise CommandError('Nenhum Ano Lectivo activo encontrado. Use --ano-letivo.')
        return ano_letivo

    def _obter_turma(self, turma_label, ano_letivo):
        classe_nome, turma_nome = TURMAS[turma_label]
        try:
            return Turma.objects.get(
                classe__nome=classe_nome, nome=turma_nome, ano_letivo=ano_letivo
            )
        except Turma.DoesNotExist:
            raise CommandError(
                f'Turma {classe_nome}/{turma_nome} não encontrada para {ano_letivo}.'
            )
