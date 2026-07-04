from django.db import models
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator
)
from alunos.models import Aluno
from professores.models import AtribuicaoDocente
from turmas.models import PeriodoAcademico

class Avaliacao(models.Model):

    atribuicao = models.ForeignKey(
        AtribuicaoDocente,
        on_delete=models.CASCADE
    )

    periodo = models.ForeignKey(
        PeriodoAcademico,
        on_delete=models.CASCADE
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        unique_together = (
            'atribuicao',
            'periodo'
        )

    def __str__(self):

        return (
            f"{self.atribuicao} - "
            f"{self.periodo}"
        )
    

class Pauta(models.Model):

    atribuicao = models.ForeignKey(
        AtribuicaoDocente,
        on_delete=models.CASCADE
    )

    periodo = models.ForeignKey(
        PeriodoAcademico,
        on_delete=models.CASCADE
    )

    fechada = models.BooleanField(
        default=False
    )

    criada_em = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return (
            f"Pauta - "
            f"{self.atribuicao}"
        )
    
class LinhaPauta(models.Model):

    pauta = models.ForeignKey(
        Pauta,
        on_delete=models.CASCADE
    )

    aluno = models.ForeignKey(
        'alunos.Aluno',
        on_delete=models.CASCADE
    )

    media = models.DecimalField(
        max_digits=4,
        decimal_places=1
    )

    aprovado = models.BooleanField(
        default=False
    )

    def verificar_situacao(self):

        frequencia = self.aluno.calcular_frequencia()

        if frequencia < 75:
            return "Reprovado por Faltas"

        if self.media >= 10:
            return "Aprovado"

        if self.media >= 8:
            return "Exame"

        return "Reprovado"
    
    def __str__(self):
        return f"{self.aluno} - {self.media}"


class ResultadoFinal(models.Model):

    aluno = models.ForeignKey(
        'alunos.Aluno',
        on_delete=models.CASCADE
    )

    disciplina = models.ForeignKey(
        'disciplinas.Disciplina',
        on_delete=models.CASCADE
    )

    ano_letivo = models.ForeignKey(
        'turmas.AnoLetivo',
        on_delete=models.CASCADE
    )

    cf = models.DecimalField(
        max_digits=4,
        decimal_places=1
    )

    situacao = models.CharField(
        max_length=50
    )

    def __str__(self):
        return f"{self.aluno} - {self.disciplina}"
    def calcular_cf(self, mt1, mt2, mt3):
        return round((mt1 + mt2 + mt3) / 3, 1)
    def verificar_situacao(self):
        if self.cf >= 10:
            return "Aprovado"
        elif self.cf >= 8:
            return "Exame"
        return "Reprovado"
    
    def save(self, *args, **kwargs):
        self.situacao = self.verificar_situacao()
        super().save(*args, **kwargs)


class Nota(models.Model):

    avaliacao = models.ForeignKey(
        Avaliacao,
        on_delete=models.CASCADE
    )

    aluno = models.ForeignKey(
        'alunos.Aluno',
        on_delete=models.CASCADE
    )

    mac = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(20)
        ]
    )

    npp = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(20)
        ]
    )

    npt = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(20)
        ]
    )

    mt = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        editable=False
    )

    observacao = models.TextField(
        blank=True,
        null=True
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    atualizado_em = models.DateTimeField(
        auto_now=True
    )

    def save(self, *args, **kwargs):
        self.mt = self.calcular_mt()
        super().save(*args, **kwargs)

    
class Meta:

    unique_together = (
        'avaliacao',
        'aluno'
    )