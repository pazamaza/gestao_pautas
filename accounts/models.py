from django.db import models
from django.contrib.auth.models import User



class Perfil(models.Model):
    user = models.OneToOneField( User,
        on_delete=models.CASCADE,
        related_name='perfil' )

    telefone = models.CharField(
        max_length=20,
        blank=True,
        null=True
)

    bi = models.CharField(
        max_length=20,
        blank=True,
        null=True
)

    morada = models.CharField(
        max_length=255,
        blank=True,
        null=True
        )

    foto = models.ImageField(
        upload_to='perfis/',
        blank=True,
        null=True
    )

    turno_coordenado = models.CharField(
        max_length=10,
        choices=[('manha', 'Manhã'), ('tarde', 'Tarde'), ('noite', 'Noite')],
        blank=True,
        verbose_name='Turno coordenado',
        help_text='Aplicável apenas a contas de Coordenador de Turno — '
                   'define quais Turmas (por turmas.Turma.periodo) esta '
                   'conta supervisiona.'
    )

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class ProfessorUser(User):
    class Meta:
        proxy = True
        verbose_name = 'Conta de Professor'
        verbose_name_plural = 'Contas de Professores'


class AlunoUser(User):
    class Meta:
        proxy = True
        verbose_name = 'Conta de Aluno'
        verbose_name_plural = 'Contas de Alunos'


class EncarregadoUser(User):
    class Meta:
        proxy = True
        verbose_name = 'Conta de Encarregado'
        verbose_name_plural = 'Contas de Encarregados'


class SubdiretorPedagogicoUser(User):
    class Meta:
        proxy = True
        verbose_name = 'Conta de Sub-diretor Pedagógico'
        verbose_name_plural = 'Contas de Sub-diretores Pedagógicos'


class DiretorGeralUser(User):
    class Meta:
        proxy = True
        verbose_name = 'Conta de Diretor Geral'
        verbose_name_plural = 'Contas de Diretores Gerais'


class ChefeSecretariaUser(User):
    class Meta:
        proxy = True
        verbose_name = 'Conta de Chefe de Secretaria'
        verbose_name_plural = 'Contas de Chefes de Secretaria'


class CoordenadorTurnoUser(User):
    class Meta:
        proxy = True
        verbose_name = 'Conta de Coordenador de Turno'
        verbose_name_plural = 'Contas de Coordenadores de Turno'


class CoordenadorPaisUser(User):
    class Meta:
        proxy = True
        verbose_name = 'Conta de Coordenador de Pais e Encarregados de Educação'
        verbose_name_plural = 'Contas de Coordenadores de Pais e Encarregados de Educação'