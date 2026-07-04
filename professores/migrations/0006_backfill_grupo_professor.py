from django.db import migrations


def adicionar_professores_ao_grupo(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Professor = apps.get_model('professores', 'Professor')

    grupo, _ = Group.objects.get_or_create(name='Professor')

    for professor in Professor.objects.select_related('user').all():
        professor.user.groups.add(grupo)


def reverter(apps, schema_editor):
    # Não remove a pertença ao grupo automaticamente: pode ter sido
    # atribuída manualmente por outros motivos entretanto.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('professores', '0005_diretorturma'),
    ]

    operations = [
        migrations.RunPython(adicionar_professores_ao_grupo, reverter),
    ]
