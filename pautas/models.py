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

    PRAZO_VALIDACAO_DIAS = 10

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

    @property
    def esta_atrasada_validacao(self):
        if self.status == self.STATUS_VALIDADA:
            return False
        limite = self.criado_em + timezone.timedelta(days=self.PRAZO_VALIDACAO_DIAS)
        return timezone.now() > limite


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
        null=True, blank=True,
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

    def eh_segundo_ano(self):
        return self.avaliacao.atribuicao.turma.eh_segundo_ano()

    def calcular_npt_terceiro_trimestre(self):
        # Regra de negócio específica do 3º trimestre: o professor não lança
        # o NPT manualmente — ele é substituído aqui pela média das médias
        # (mt) do 1º e 2º trimestre já lançadas para o mesmo aluno/disciplina/
        # turma/ano letivo. Por isso levanta ValueError se essas notas
        # anteriores ainda não existirem (não há como calcular o 3º sem elas).
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
        # MT (média do trimestre) = média aritmética simples de MAC e NPT,
        # arredondada à unidade mais próxima ("Base Legal" EJA — ex.: 13,5 -> 14).
        media = (self.mac + self.npt) / Decimal('2')
        return media.quantize(Decimal('1'), rounding=ROUND_HALF_UP)

    def calcular_mt_com_exame(self):
        # IIº Ano EJA, 3º trimestre: o NPT dá lugar à NE (Nota de Exame),
        # lançada pelo professor no mesmo ecrã que o MAC. O MT desse
        # trimestre pondera os dois — MAC 40% / NE 60% — em vez da média
        # simples usada nos restantes trimestres.
        media = (self.mac * Decimal('0.40')) + (self.npt * Decimal('0.60'))
        return media.quantize(Decimal('1'), rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        terceiro_trimestre = self.eh_terceiro_trimestre()

        if terceiro_trimestre and self.eh_segundo_ano():
            # IIº Ano EJA: o NPT do 3º trimestre é, na prática, a NE (Nota
            # de Exame) — continua a ser exigido no formulário, só muda o
            # peso com que entra no MT (ver calcular_mt_com_exame).
            self.mt = self.calcular_mt_com_exame()
        elif terceiro_trimestre:
            # Iº Ano (e qualquer Classe fora do IIº Ano EJA): o NPT é sempre
            # recalculado (ver calcular_npt_terceiro_trimestre) antes de
            # gravar — mesmo que o formulário tenha enviado outro valor.
            self.npt = self.calcular_npt_terceiro_trimestre()
            self.mt = self.calcular_mt()
        else:
            self.mt = self.calcular_mt()

        # Se a gravação vier com update_fields (ex.: form.save() que só
        # actualiza os campos alterados), garantimos que 'mt'/'npt' entram
        # sempre na lista — senão o Django ignora estes 2 campos recalculados
        # acima e a média fica "congelada" no valor da 1ª gravação.
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            kwargs['update_fields'] = set(update_fields) | {'mt', 'npt'}

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

    en = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='Exame Nacional',
        help_text='Só se aplica ao IIº Ano EJA — entra na MFED = MFD + (EN×0,40)/2.'
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
    RESULTADO_REPROVADO_FALTAS = 'Reprovado por Faltas'
    RESULTADO_RECURSO = 'Recurso'
    # Legado: produzidos por fórmulas anteriores (pesos 25/35/40 + exame
    # escolar; depois MFD/MFED + Exame Nacional), entretanto substituídas.
    # Mantidos só para não quebrar a leitura de resultados antigos já
    # gravados; a lógica actual (abaixo) nunca os atribui.
    RESULTADO_EXAME = 'Exame'
    RESULTADO_DEFICIENCIA = 'Deficiência'
    RESULTADO_AGUARDA_EXAME_NACIONAL = 'Aguarda Exame Nacional'

    PRAZO_HOMOLOGACAO_DIAS = 3

    homologado_por = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    homologado_em = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:

        unique_together = (
            'aluno',
            'disciplina',
            'ano_letivo'
        )

    def eh_segundo_ano(self):
        return self.aluno.turma.eh_segundo_ano()

    def excedeu_limite_faltas(self):
        from pautas.services.faltas import aluno_excedeu_faltas_disciplina
        return aluno_excedeu_faltas_disciplina(self.aluno, self.disciplina, self.ano_letivo)

    def homologar(self, user):
        self.homologado_por = user
        self.homologado_em = timezone.now()
        self.save()

    @property
    def esta_atrasada_homologacao(self):
        if self.status != self.STATUS_VALIDADA or self.homologado_em or not self.validado_em:
            return False
        limite = self.validado_em + timezone.timedelta(days=self.PRAZO_HOMOLOGACAO_DIAS)
        return timezone.now() > limite

    def calcular_mf(self):
        # MF (Iº Ano: "MFD"; IIº Ano: "MFA") = média simples das 3 médias
        # trimestrais, sem pesos — mesma fórmula nos dois anos. A única
        # diferença entre anos está em COMO mt3 é calculado a montante
        # (Nota.calcular_mt vs. calcular_mt_com_exame, ver models.py:Nota).
        valor = (self.mt1 + self.mt2 + self.mt3) / Decimal('3')
        return self.arredondar_nota(valor)

    def calcular_nota_final(self):
        # Campo legado (MFED, fórmula anterior) — já não é usado por
        # nenhum dos dois anos; a nota_recurso (nota seca) é quem decide
        # agora, directamente sobre a MF/MFA (ver verificar_resultado).
        return None

    def verificar_resultado(self):
        if self.excedeu_limite_faltas():
            # Veto absoluto: reprova a disciplina independentemente das
            # notas (regra de faltas por tempos lectivos semanais da "Base
            # Legal" — ver services/faltas.py). Não entra na tolerância de
            # aprovação nem no recurso.
            return self.RESULTADO_REPROVADO_FALTAS

        if self.eh_segundo_ano() and self.nota_recurso is not None:
            # Nota de recurso é nota seca (substitui a MFA por completo);
            # só conta como aprovação se >=10. O Iº Ano não tem recurso —
            # um nota_recurso lá gravado (não deveria acontecer, o campo é
            # só editável por superuser) é ignorado propositadamente.
            return (
                self.RESULTADO_APROVADO
                if self.nota_recurso >= 10
                else self.RESULTADO_REPROVADO
            )

        if self.eh_segundo_ano():
            return self._verificar_resultado_segundo_ano()
        return self._verificar_resultado_primeiro_ano()

    def _verificar_resultado_primeiro_ano(self):
        # Iº Ano: sem recurso — a MF decide sozinha por disciplina. A
        # tolerância de até 2 disciplinas entre 8-9 (excepto
        # Português+Matemática em simultâneo) é uma regra ANUAL, avaliada
        # em services/resultados.py:verificar_transicao_aluno, não aqui.
        if self.mf >= 10:
            return self.RESULTADO_APROVADO
        return self.RESULTADO_REPROVADO

    def _verificar_resultado_segundo_ano(self):
        # IIº Ano: disciplinas com MFA 7-9 têm direito a Exame de Recurso
        # (NER, nota seca) — ficam "Recurso" (pendente) até essa nota ser
        # lançada, ou até o veto do gatilho (mais de 4 disciplinas em
        # recurso, ou L.Portuguesa+Matemática simultâneas nessa banda) as
        # fechar directamente como Reprovado — ver services/resultados.py:
        # _transicao_segundo_ano. MFA<=6 reprova de imediato, sem direito a
        # recurso.
        if self.mf <= 6:
            return self.RESULTADO_REPROVADO
        if self.mf >= 10:
            return self.RESULTADO_APROVADO
        return self.RESULTADO_RECURSO

    def arredondar_nota(self, valor):
        # "Base Legal": arredondamento à unidade mais próxima em TODAS as
        # médias (ex.: 9,5 -> 10; HALF_UP cobre exactamente este caso) —
        # substitui a regra anterior, que só arredondava à unidade numa
        # banda estreita (9,5-10) e mantinha 1 casa decimal no resto.
        return Decimal(valor).quantize(Decimal('1'), rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        self.mf = self.calcular_mf()
        self.nota_final = self.calcular_nota_final()
        self.resultado = self.verificar_resultado()
        super().save(*args, **kwargs)

class ResultadoFinal(models.Model):
    # LEGADO: não é usado por nenhuma view activa (ver CLAUDE.md). O cálculo
    # de resultado em produção é feito por ResultadoDisciplina, com pesos
    # 25/35/40 (calcular_mf) — este modelo usa média simples dos 3 trimestres
    # (calcular_cf) e não deve ser usado como base para código novo.

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
    TIPO_DECLARACAO = 'declaracao'
    TIPO_CERTIFICADO = 'certificado'
    TIPO_CHOICES = [
        (TIPO_BOLETIM, 'Boletim de Notas'),
        (TIPO_DECLARACAO, 'Declaração de Notas'),
        (TIPO_CERTIFICADO, 'Certificado'),
    ]

    STATUS_PENDENTE = 'pendente'
    STATUS_RECUSADO = 'recusado'
    STATUS_AUTORIZADO = 'autorizado'
    STATUS_PAGAMENTO_SUBMETIDO = 'pagamento_submetido'
    STATUS_PAGAMENTO_CONFIRMADO = 'pagamento_confirmado'
    STATUS_EMITIDO = 'emitido'
    STATUS_AUTENTICADO = 'autenticado'
    STATUS_PRONTO = 'pronto_levantamento'
    STATUS_LEVANTADO = 'levantado'

    STATUS_CHOICES = [
        (STATUS_PENDENTE, 'Pendente de Autorização'),
        (STATUS_RECUSADO, 'Recusado'),
        (STATUS_AUTORIZADO, 'Autorizado - Aguarda Pagamento'),
        (STATUS_PAGAMENTO_SUBMETIDO, 'Comprovativo Submetido'),
        (STATUS_PAGAMENTO_CONFIRMADO, 'Pagamento Confirmado - Aguarda Emissão'),
        (STATUS_EMITIDO, 'Emitido - Aguarda Autenticação'),
        (STATUS_AUTENTICADO, 'Autenticado - Aguarda Notificação'),
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

    forma_pagamento = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Forma de Pagamento',
        help_text='Indicada pela Secretaria ao autorizar o pedido (ex.: Transferência GPS/Ruper, referência de pagamento).'
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

    emitido_por = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name='Emitido por (Secretaria)'
    )

    emitido_em = models.DateTimeField(
        null=True,
        blank=True
    )

    autenticado_por = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name='Autenticado por (Diretor Geral/Sub-diretor/Diretor de Turma)'
    )

    autenticado_em = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-solicitado_em']
        verbose_name = 'Pedido de Documento'
        verbose_name_plural = 'Pedidos de Documentos'

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.aluno} - {self.get_status_display()}"

    def autorizar(self, user, forma_pagamento):
        self.status = self.STATUS_AUTORIZADO
        self.autorizado_por = user
        self.decidido_em = timezone.now()
        self.forma_pagamento = forma_pagamento
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
        # Deixa de ir directamente para "Pronto para Levantamento" — antes
        # do aluno ser chamado, o documento ainda tem de ser emitido pela
        # Secretaria e autenticado por quem de direito (ver emitir/autenticar).
        self.pagamento_confirmado_por = user
        self.pagamento_confirmado_em = timezone.now()
        self.status = self.STATUS_PAGAMENTO_CONFIRMADO
        self.save()

    def rejeitar_pagamento(self, user):
        self.pagamento_confirmado_por = None
        self.pagamento_confirmado_em = None
        self.comprovativo_pagamento = None
        self.pagamento_submetido_em = None
        self.status = self.STATUS_AUTORIZADO
        self.save()

    def emitir(self, user):
        self.emitido_por = user
        self.emitido_em = timezone.now()
        self.status = self.STATUS_EMITIDO
        self.save()

    def autenticar(self, user):
        self.autenticado_por = user
        self.autenticado_em = timezone.now()
        self.status = self.STATUS_AUTENTICADO
        self.save()

    def marcar_pronto(self):
        self.status = self.STATUS_PRONTO
        self.save()

    def marcar_levantado(self):
        self.status = self.STATUS_LEVANTADO
        self.save()
