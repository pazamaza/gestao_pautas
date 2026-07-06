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


class AdministradorUser(User):
    class Meta:
        proxy = True
        verbose_name = 'Conta de Administrador'
        verbose_name_plural = 'Contas de Administradores'