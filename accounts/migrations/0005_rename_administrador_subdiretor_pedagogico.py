from django.db import migrations


def renomear_grupo_administrador(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='Administrador').update(name='Sub-diretor Pedagógico')


def renomear_grupo_de_volta(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='Sub-diretor Pedagógico').update(name='Administrador')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_administradoruser_alunouser_encarregadouser_and_more'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='AdministradorUser',
            new_name='SubdiretorPedagogicoUser',
        ),
        migrations.AlterModelOptions(
            name='subdiretorpedagogicouser',
            options={
                'verbose_name': 'Conta de Sub-diretor Pedagógico',
                'verbose_name_plural': 'Contas de Sub-diretores Pedagógicos',
            },
        ),
        migrations.RunPython(
            renomear_grupo_administrador,
            reverse_code=renomear_grupo_de_volta,
        ),
    ]
