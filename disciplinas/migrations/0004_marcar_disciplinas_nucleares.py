from django.db import migrations


NOMES_NUCLEARES = [
    'Matemática',
    'Matematica',
    'Língua Portuguesa',
    'Lingua Portuguesa',
]


def marcar_nucleares(apps, schema_editor):
    Disciplina = apps.get_model('disciplinas', 'Disciplina')
    Disciplina.objects.filter(nome__in=NOMES_NUCLEARES).update(nuclear=True)


def reverter(apps, schema_editor):
    Disciplina = apps.get_model('disciplinas', 'Disciplina')
    Disciplina.objects.filter(nome__in=NOMES_NUCLEARES).update(nuclear=False)


class Migration(migrations.Migration):

    dependencies = [
        ('disciplinas', '0003_disciplina_nuclear'),
    ]

    operations = [
        migrations.RunPython(marcar_nucleares, reverter),
    ]
