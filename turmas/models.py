from django.db import models
from django.utils import timezone


class AnoLetivo(models.Model):

    descricao = models.CharField(
        max_length=20,
        unique=True
    )

    ativo = models.BooleanField(
        default=True
    )

    class Meta:
        ordering = ['-descricao']
        verbose_name = 'Ano Letivo'
        verbose_name_plural = 'Anos Letivos'

    def __str__(self):
        return self.descricao


class PeriodoAcademico(models.Model):

    nome = models.CharField(
        max_length=50
    )

    ano_letivo = models.ForeignKey(
        AnoLetivo,
        on_delete=models.CASCADE
    )

    aberto = models.BooleanField(
        default=True
    )

    data_inicio_lancamento = models.DateField(
        null=True,
        blank=True,
        verbose_name='Início do lançamento de notas'
    )

    data_fim_lancamento = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fim do lançamento de notas'
    )

    class Meta:
        verbose_name = 'Período Académico'
        verbose_name_plural = 'Períodos Académicos'

    def __str__(self):
        return f"{self.nome} - {self.ano_letivo}"

    def periodo_lancamento_ativo(self):
        if not self.aberto:
            return False

        hoje = timezone.localdate()

        if self.data_inicio_lancamento and hoje < self.data_inicio_lancamento:
            return False

        if self.data_fim_lancamento and hoje > self.data_fim_lancamento:
            return False

        return True


class Classe(models.Model):
    nome = models.CharField(
        max_length=20,
        unique=True
    )
    class Meta:
        ordering = ['nome']
    def __str__(self):
        return self.nome


class Turma(models.Model):
    nome = models.CharField(
        max_length=20    )
    classe = models.ForeignKey(
        Classe,
        on_delete=models.PROTECT
    )
    ano_letivo = models.ForeignKey(
        AnoLetivo,
        on_delete=models.PROTECT
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativa"
    )
    class Meta:
        unique_together = ('nome', 'classe', 'ano_letivo'  )
    def __str__(self):
        return (f"{self.classe} " f"{self.nome} - " f"{self.ano_letivo}" )
    
