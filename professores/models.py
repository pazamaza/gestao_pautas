from django.db import models
from django.contrib.auth.models import User
from disciplinas.models import Disciplina

class Professor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE    )
    numero_funcionario = models.CharField(
        max_length=30,
        unique=True
    )
    telefone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
   
    ativo = models.BooleanField(
        default=True
    )
    criado_em = models.DateTimeField(
        auto_now_add=True
    )
    def __str__(self):
        nome = self.user.get_full_name()
        if nome:
            return nome
        return self.user.username
    
class AtribuicaoDocente(models.Model):

    professor = models.ForeignKey(
        Professor,
        on_delete=models.CASCADE
    )

    disciplina = models.ForeignKey(
        'disciplinas.Disciplina',
        on_delete=models.CASCADE
    )

    turma = models.ForeignKey(
        'turmas.Turma',
        on_delete=models.CASCADE
    )

    ano_letivo = models.ForeignKey(
        'turmas.AnoLetivo',
        on_delete=models.CASCADE
    )

    ativo = models.BooleanField(
        default=True
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        unique_together = (
            'professor',
            'disciplina',
            'turma',
            'ano_letivo'
        )

    def __str__(self):

        return (
            f"{self.professor} | "
            f"{self.disciplina} | "
            f"{self.turma}"
        )


class DiretorTurma(models.Model):

    professor = models.ForeignKey(
        Professor,
        on_delete=models.CASCADE
    )

    turma = models.ForeignKey(
        'turmas.Turma',
        on_delete=models.CASCADE
    )

    ano_letivo = models.ForeignKey(
        'turmas.AnoLetivo',
        on_delete=models.CASCADE
    )

    ativo = models.BooleanField(
        default=True
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        unique_together = (
            'turma',
            'ano_letivo'
        )

        verbose_name = 'Diretor de Turma'
        verbose_name_plural = 'Diretores de Turma'

    def __str__(self):

        return (
            f"{self.professor} - "
            f"{self.turma}"
        )