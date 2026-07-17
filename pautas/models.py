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
    npt = models.DecimalField(max_digits=4, decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(20)
        ])
    mt = models.DecimalField(max_digits=4, decimal_places=1,
        editable=False)
    observacao = models.TextField(blank=True, null=True )
    criado_em = models.DateTimeField(auto_now_add=True )
    atualizado_em = models.DateTimeField(auto_now=True)

    def eh_terceiro_trimestre(self):
        from pautas.services.periodos import campo_periodo
        return campo_periodo(self.avaliacao.periodo) == 'mt3'

    def calcular_npt_terceiro_trimestre(self):
        from pautas.services.periodos import campo_periodo

        atribuicao = self.avaliacao.atribuicao
        notas_anteriores = Nota.objects.filter(
            aluno=self.aluno,
            avaliacao__atribuicao__disciplina=atribuicao.disciplina,
            avaliacao__atribuicao__turma=atribuicao.turma,
            avaliacao__atribuicao__ano_letivo=atribuicao.ano_letivo,
        ).exclude(pk=self.pk).select_related('avaliacao__periodo')

        medias = {}
        for nota in notas_anteriores:
            campo = campo_periodo(nota.avaliacao.periodo)
            if campo in ('mt1', 'mt2'):
                medias[campo] = nota.mt

        if 'mt1' not in medias or 'mt2' not in medias:
            raise ValueError(
                'É necessário lançar as notas do 1º e 2º trimestre antes do 3º.'
            )

        return (medias['mt1'] + medias['mt2']) / Decimal('2')

    def calcular_mt(self):
        media = (self.mac + self.npt) / Decimal('2')
        return media.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        if self.eh_terceiro_trimestre():
            self.npt = self.calcular_npt_terceiro_trimestre()
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
        return self.arredondar_nota(self.mt3)

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


class PedidoDocumento(models.Model):

    TIPO_BOLETIM = 'boletim'
    TIPO_CERTIFICADO = 'certificado'
    TIPO_CHOICES = [
        (TIPO_BOLETIM, 'Boletim de Notas'),
        (TIPO_CERTIFICADO, 'Certificado'),
    ]

    STATUS_PENDENTE = 'pendente'
    STATUS_RECUSADO = 'recusado'
    STATUS_AUTORIZADO = 'autorizado'
    STATUS_PAGAMENTO_SUBMETIDO = 'pagamento_submetido'
    STATUS_PRONTO = 'pronto_levantamento'
    STATUS_LEVANTADO = 'levantado'

    STATUS_CHOICES = [
        (STATUS_PENDENTE, 'Pendente de Autorização'),
        (STATUS_RECUSADO, 'Recusado'),
        (STATUS_AUTORIZADO, 'Autorizado - Aguarda Pagamento'),
        (STATUS_PAGAMENTO_SUBMETIDO, 'Comprovativo Submetido'),
        (STATUS_PRONTO, 'Pronto para Levantamento'),
        (STATUS_LEVANTADO, 'Levantado'),
    ]

    aluno = models.ForeignKey(
        'alunos.Aluno',
        on_delete=models.CASCADE
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES
    )

    ano_letivo = models.ForeignKey(
        'turmas.AnoLetivo',
        on_delete=models.CASCADE
    )

    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default=STATUS_PENDENTE
    )

    solicitado_em = models.DateTimeField(
        auto_now_add=True
    )

    autorizado_por = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    decidido_em = models.DateTimeField(
        null=True,
        blank=True
    )

    motivo_recusa = models.TextField(
        blank=True
    )

    comprovativo_pagamento = models.ImageField(
        upload_to='pagamentos/',
        null=True,
        blank=True
    )

    pagamento_submetido_em = models.DateTimeField(
        null=True,
        blank=True
    )

    pagamento_confirmado_por = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    pagamento_confirmado_em = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-solicitado_em']
        verbose_name = 'Pedido de Documento'
        verbose_name_plural = 'Pedidos de Documentos'

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.aluno} - {self.get_status_display()}"

    def autorizar(self, user):
        self.status = self.STATUS_AUTORIZADO
        self.autorizado_por = user
        self.decidido_em = timezone.now()
        self.save()

    def recusar(self, user, motivo):
        self.status = self.STATUS_RECUSADO
        self.autorizado_por = user
        self.decidido_em = timezone.now()
        self.motivo_recusa = motivo
        self.save()

    def submeter_pagamento(self, comprovativo):
        self.comprovativo_pagamento = comprovativo
        self.pagamento_submetido_em = timezone.now()
        self.status = self.STATUS_PAGAMENTO_SUBMETIDO
        self.save()

    def confirmar_pagamento(self, user):
        self.pagamento_confirmado_por = user
        self.pagamento_confirmado_em = timezone.now()
        self.status = self.STATUS_PRONTO
        self.save()

    def rejeitar_pagamento(self, user):
        self.pagamento_confirmado_por = None
        self.pagamento_confirmado_em = None
        self.comprovativo_pagamento = None
        self.pagamento_submetido_em = None
        self.status = self.STATUS_AUTORIZADO
        self.save()

    def marcar_levantado(self):
        self.status = self.STATUS_LEVANTADO
        self.save()
