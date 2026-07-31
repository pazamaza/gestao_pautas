from django.core.management.base import BaseCommand

from pautas.models import ResultadoDisciplina


class Command(BaseCommand):
    help = (
        'Recalcula o campo "resultado" (e "mf") de todos os ResultadoDisciplina '
        'já existentes, sem apagar nem recriar nada — ao contrário de '
        '"Gerar Resultados" (gerar_resultados_finais), preserva nota_recurso e o '
        'status de validação já atribuído. Útil sempre que uma regra de negócio '
        'de cálculo/recurso muda depois de já existirem resultados gravados.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--ano-letivo', type=int, default=None,
            help='Limita o recálculo a um ano lectivo específico (id). Por omissão, recalcula todos.',
        )

    def handle(self, *args, **options):
        queryset = ResultadoDisciplina.objects.select_related('disciplina', 'aluno__turma__classe')
        ano_letivo_id = options['ano_letivo']
        if ano_letivo_id:
            queryset = queryset.filter(ano_letivo_id=ano_letivo_id)

        total = 0
        alterados = 0
        for resultado in queryset:
            resultado_anterior = resultado.resultado
            resultado.save()
            total += 1
            if resultado.resultado != resultado_anterior:
                alterados += 1

        self.stdout.write(self.style.SUCCESS(
            f'{total} resultado(s) recalculado(s), {alterados} com classificação alterada.'
        ))
