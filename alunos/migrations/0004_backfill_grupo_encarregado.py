from django.db import migrations


def adicionar_encarregados_ao_grupo(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Encarregado = apps.get_model('alunos', 'Encarregado')

    grupo, _ = Group.objects.get_or_create(name='Encarregado')

    for encarregado in Encarregado.objects.select_related('user').all():
        encarregado.user.groups.add(grupo)


def reverter(apps, schema_editor):
    # Não remove a pertença ao grupo automaticamente: pode ter sido
    # atribuída manualmente por outros motivos entretanto.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('alunos', '0003_aluno_user'),
    ]

    operations = [
        migrations.RunPython(adicionar_encarregados_ao_grupo, reverter),
    ]
