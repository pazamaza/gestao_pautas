from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.core.validators import (MinValueValidator,
    MaxValueValidator)
from alunos.models import Aluno
from professores.models import AtribuicaoDocente
from turmas.models import PeriodoAcademico
from decimal import Decimal, ROUND_HALF_UP


class StatusValidacaoMixin(models.Model):
    STATUS_RASCUNHO = 'rascunho'
    STATUS_COM_ERROS = 'com_erros'
    STATUS_VALIDADA = 'validada'

    STATUS_CHOICES = [
        (STATUS_RASCUNHO, 'Rascunho'),
        (STATUS_COM_ERROS, 'Com Erros'),
        (STATUS_VALIDADA, 'Validada'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_RASCUNHO
    )

    validado_por = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    validado_em = models.DateTimeField(
        null=True,
        blank=True
    )

    observacoes_validacao = models.TextField(
        blank=True
    )

    class Meta:
        abstract = True

    def marcar_validada(self, user):
        self.status = self.STATUS_VALIDADA
        self.validado_por = user
        self.validado_em = timezone.now()
        self.save()

    def marcar_com_erros(self, user, observacoes):
        self.status = self.STATUS_COM_ERROS
        self.validado_por = user
        self.validado_em = timezone.now()
        self.observacoes_validacao = observacoes
        self.save()


class Avaliacao(StatusValidacaoMixin, models.Model):

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


class Nota(models.Model):
    avaliacao = models.ForeignKey(Avaliacao,
        on_delete=models.CASCADE)
    aluno = models.ForeignKey('alunos.Aluno',
        on_delete=models.CASCADE)
    mac = models.DecimalField(max_digits=4, decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(20)]
    )
    npp = models.DecimalField(max_digits=4, decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(20)
        ])
    npt = models.DecimalField(max_digits=4, decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(20)
        ])
    mt = models.DecimalField(max_digits=4, decimal_places=1,
        editable=False)
    observacao = models.TextField(blank=True, null=True )
    criado_em = models.DateTimeField(auto_now_add=True )
    atualizado_em = models.DateTimeField(auto_now=True)

    def calcular_mt(self):
        media = (self.mac + self.npp + self.npt) / Decimal('3')
        return media.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        self.mt = self.calcular_mt()
        super().save(*args, **kwargs)
    
    class Meta:
        unique_together = ('avaliacao','aluno')

    def __str__(self):
        return f"{self.aluno} - {self.mt}"

class ResultadoDisciplina(StatusValidacaoMixin, models.Model):

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

    mt1 = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0
    )

    mt2 = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0
    )

    mt3 = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0
    )

    mf = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0
    )

    exame = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True
    )

    resultado = models.CharField(
        max_length=30,
        blank=True
    )

    nota_final = models.DecimalField(
    max_digits=4,
    decimal_places=1,
    null=True,
    blank=True
)

    nota_recurso = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='Nota de Recurso',
        help_text='Nota seca: quando preenchida, torna-se a nota final da disciplina.'
    )

    RESULTADO_APROVADO = 'Aprovado'
    RESULTADO_REPROVADO = 'Reprovado'
    RESULTADO_EXAME = 'Exame'
    RESULTADO_RECURSO = 'Recurso'
    RESULTADO_DEFICIENCIA = 'Deficiência'

    class Meta:

        unique_together = (
            'aluno',
            'disciplina',
            'ano_letivo'
        )

    def calcular_mf(self):
        valor = ((self.mt1 * Decimal('0.25')) + (self.mt2 * Decimal('0.35')) +
            (self.mt3 * Decimal('0.40'))    )
        return self.arredondar_nota(valor)

    def calcular_nota_final(self):
        if self.nota_recurso is not None:
            return self.nota_recurso
        if self.exame is None:
            return None
        valor = (self.mf + self.exame) / 2
        return self.arredondar_nota(valor)

    def verificar_resultado(self):
        if self.mf < 8:
            return self.RESULTADO_REPROVADO
        if self.mf >= 10:
            return self.RESULTADO_APROVADO

        if self.exame is None:
            return self.RESULTADO_EXAME

        nota_final = self.calcular_nota_final()
        if nota_final >= 10:
            return self.RESULTADO_APROVADO
        if nota_final < 8:
            return self.RESULTADO_REPROVADO

        if self.disciplina.nuclear:
            return self.RESULTADO_REPROVADO
        if self.nota_recurso is None:
            return self.RESULTADO_RECURSO
        return self.RESULTADO_DEFICIENCIA

    def arredondar_nota(self, valor):
        valor = Decimal(valor).quantize(
            Decimal('0.1'),
            rounding=ROUND_HALF_UP
        )
        if 9.5 <= valor < 10:
            return Decimal('10.0')
        return valor
    
    def save(self, *args, **kwargs):            
        self.mf = self.calcular_mf()
        self.nota_final = (self.calcular_nota_final())        
        self.resultado = (self.verificar_resultado())
        super().save(*args, **kwargs)

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

    mt1 = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0
    )

    mt2 = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0
    )

    mt3 = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0
    )

    cf = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0
    )

    exame = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        blank=True,
        null=True
    )

    situacao = models.CharField(
        max_length=30,
        blank=True
    )

    def calcular_cf(self):

        return round(
            (self.mt1 + self.mt2 + self.mt3) / 3,
            1
        )

    def verificar_situacao(self):

        if self.cf >= 10:
            return "Aprovado"

        elif self.cf >= 8:
            return "Exame"

        return "Reprovado"

    def calcular_nota_final_exame(self):

        if self.exame is None:
            return None

        return round(
            (self.cf + self.exame) / 2,
            1
        )

    def save(self, *args, **kwargs):

        self.cf = self.calcular_cf()

        self.situacao = self.verificar_situacao()

        super().save(*args, **kwargs)

    def __str__(self):

        return (
            f"{self.aluno} - "
            f"{self.disciplina}"
        )


class SituacaoAnual(models.Model):

    SITUACAO_APROVADO = 'Aprovado'
    SITUACAO_APROVADO_COMPENSACAO = 'Aprovado por Compensação'
    SITUACAO_REPROVADO = 'Reprovado'

    SITUACAO_CHOICES = [
        (SITUACAO_APROVADO, 'Aprovado'),
        (SITUACAO_APROVADO_COMPENSACAO, 'Aprovado por Compensação'),
        (SITUACAO_REPROVADO, 'Reprovado'),
    ]

    aluno = models.ForeignKey(
        'alunos.Aluno',
        on_delete=models.CASCADE
    )

    ano_letivo = models.ForeignKey(
        'turmas.AnoLetivo',
        on_delete=models.CASCADE
    )

    situacao = models.CharField(
        max_length=30,
        choices=SITUACAO_CHOICES,
        blank=True
    )

    disciplinas_em_deficiencia = models.ManyToManyField(
        'disciplinas.Disciplina',
        blank=True,
        related_name='+'
    )

    calculado_em = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        unique_together = (
            'aluno',
            'ano_letivo'
        )

        verbose_name = 'Situação Anual'
        verbose_name_plural = 'Situações Anuais'

    def __str__(self):

        return (
            f"{self.aluno} - "
            f"{self.ano_letivo} - "
            f"{self.situacao}"
        )
