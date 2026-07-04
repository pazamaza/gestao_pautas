from django.db import migrations


CLASSES = ['7ª Classe', '8ª Classe', '9ª Classe']
LETRAS = ['A', 'B', 'C']


def criar_classes_e_turmas(apps, schema_editor):
    Classe = apps.get_model('turmas', 'Classe')
    Turma = apps.get_model('turmas', 'Turma')
    AnoLetivo = apps.get_model('turmas', 'AnoLetivo')

    classes = []
    for nome in CLASSES:
        classe, _ = Classe.objects.get_or_create(nome=nome)
        classes.append(classe)

    for ano_letivo in AnoLetivo.objects.all():
        for classe in classes:
            for letra in LETRAS:
                Turma.objects.get_or_create(
                    nome=letra,
                    classe=classe,
                    ano_letivo=ano_letivo,
                    defaults={'ativo': True},
                )


def remover_seed(apps, schema_editor):
    # Não remove nada automaticamente: as turmas podem já ter alunos
    # matriculados por altura em que esta migração for revertida.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('turmas', '0004_periodoacademico_data_fim_lancamento_and_more'),
    ]

    operations = [
        migrations.RunPython(criar_classes_e_turmas, remover_seed),
    ]
