from django.db import models


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

    class Meta:
        verbose_name = 'Período Académico'
        verbose_name_plural = 'Períodos Académicos'

    def __str__(self):
        return f"{self.nome} - {self.ano_letivo}"


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
    
