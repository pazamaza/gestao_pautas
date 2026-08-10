from django.db import migrations

GRUPOS = [
    'Diretor Geral do Complexo',
    'Chefe de Secretaria',
    'Coordenador de Turno',
    'Coordenador de Pais e Encarregados de Educação',
]


def criar_grupos(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for nome in GRUPOS:
        Group.objects.get_or_create(name=nome)


def remover_grupos(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=GRUPOS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_chefesecretariauser_coordenadorpaisuser_and_more'),
    ]

    operations = [
        migrations.RunPython(criar_grupos, reverse_code=remover_grupos),
    ]
