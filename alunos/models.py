from datetime import date

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from turmas.models import Turma

class Encarregado(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    telefone = models.CharField(
        max_length=20
    )

    profissao = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    def __str__(self):
        nome = self.user.get_full_name()
        if nome:
            return nome
        return self.user.username

class Aluno(models.Model):

    ESTADO_ATIVO = 'ativo'
    ESTADO_TRANSFERIDO = 'transferido'

    ESTADO_CHOICES = (
        (ESTADO_ATIVO, 'Ativo'),
        (ESTADO_TRANSFERIDO, 'Transferido'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='aluno'
    )

    nome = models.CharField(
        max_length=200
    )

    numero_processo = models.CharField(
        max_length=30,
        unique=True
    )

    data_nascimento = models.DateField()

    sexo = models.CharField(
        max_length=1,
        choices=(
            ('M', 'Masculino'),
            ('F', 'Feminino')
        )
    )

    turma = models.ForeignKey(
        Turma,
        on_delete=models.PROTECT
    )

    encarregado = models.ForeignKey(
        Encarregado,
        on_delete=models.PROTECT
    )

    foto = models.ImageField(
        upload_to='alunos/',
        blank=True,
        null=True
    )

    nome_pai = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Nome do pai'
    )

    nome_mae = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Nome da mãe'
    )

    naturalidade = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Naturalidade',
        help_text='Cidade/comuna de nascimento.'
    )

    municipio_natural = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Município de naturalidade'
    )

    provincia_natal = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Província de naturalidade'
    )

    numero_bi = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='Número do B.I.'
    )

    local_emissao_bi = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Local de emissão do B.I.',
        help_text='Ex.: Arquivo Nacional de Identificação de Luanda.'
    )

    data_emissao_bi = models.DateField(
        null=True,
        blank=True,
        verbose_name='Data de emissão do B.I.'
    )

    foto_bi = models.FileField(
        upload_to='alunos/bi/',
        blank=True,
        null=True,
        verbose_name='Fotocópia do B.I.'
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=ESTADO_ATIVO
    )

    criado_em = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True
    )

    atualizado_em = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.nome

    def calcular_frequencia(self):
        total = self.frequencia_set.count()
        presentes = self.frequencia_set.filter(
            estado__in=['P', 'A']
        ).count()

        if total == 0:
            return 0

        return round(
            (presentes / total) * 100,
            2
        )

    def calcular_idade(self):
        hoje = date.today()
        return hoje.year - self.data_nascimento.year - (
            (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day)
        )

    def dados_certificado_completos(self):
        """Dados civis exigidos para emitir o Certificado — a filiação
        paterna fica de fora porque nem todo aluno tem o pai indicado."""
        campos_obrigatorios = (
            self.nome_mae, self.naturalidade, self.municipio_natural,
            self.provincia_natal, self.numero_bi, self.local_emissao_bi,
        )
        return all(campos_obrigatorios) and self.data_emissao_bi is not None and bool(self.foto_bi)

    def total_faltas(self):
        return self.frequencia_set.filter(estado='F').count()

    def contar_faltas_injustificadas(self, ano_letivo=None, disciplina=None, turma=None):
        qs = self.frequencia_set.filter(estado='F').select_related(
            'justificacaofalta', 'atribuicao'
        )
        if ano_letivo:
            qs = qs.filter(atribuicao__ano_letivo=ano_letivo)
        if disciplina:
            qs = qs.filter(atribuicao__disciplina=disciplina)
        if turma:
            qs = qs.filter(atribuicao__turma=turma)
        return sum(1 for frequencia in qs if frequencia.esta_injustificada())

class Matricula(models.Model):

    aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE
    )

    turma = models.ForeignKey(
        Turma,
        on_delete=models.PROTECT
    )

    data_matricula = models.DateField(
        auto_now_add=True
    )

    ano_letivo = models.ForeignKey(
        'turmas.AnoLetivo',
        on_delete=models.PROTECT
    )

    ativa = models.BooleanField(
        default=True
    )

    def __str__(self):
        return f"{self.aluno} - {self.turma}"


class Reclamacao(models.Model):
    """Reclamação de um Encarregado de Educação, registada pelo
    Coordenador de Pais e Encarregados de Educação (ponto de contacto) e
    encaminhada ao Diretor Geral ou ao Sub-diretor Pedagógico consoante a
    natureza do assunto."""

    ENCAMINHAMENTO_DIRETOR_GERAL = 'diretor_geral'
    ENCAMINHAMENTO_SUBDIRETOR_PEDAGOGICO = 'subdiretor_pedagogico'
    ENCAMINHAMENTO_CHOICES = [
        (ENCAMINHAMENTO_DIRETOR_GERAL, 'Diretor Geral'),
        (ENCAMINHAMENTO_SUBDIRETOR_PEDAGOGICO, 'Sub-diretor Pedagógico'),
    ]

    ESTADO_ABERTA = 'aberta'
    ESTADO_ENCAMINHADA = 'encaminhada'
    ESTADO_RESOLVIDA = 'resolvida'
    ESTADO_CHOICES = [
        (ESTADO_ABERTA, 'Aberta'),
        (ESTADO_ENCAMINHADA, 'Encaminhada'),
        (ESTADO_RESOLVIDA, 'Resolvida'),
    ]

    encarregado = models.ForeignKey(
        Encarregado,
        on_delete=models.CASCADE,
        related_name='reclamacoes'
    )

    aluno = models.ForeignKey(
        'alunos.Aluno',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reclamacoes',
        help_text='Educando a que a reclamação se refere, se aplicável.'
    )

    motivo = models.TextField()

    estado = models.CharField(
        max_length=15,
        choices=ESTADO_CHOICES,
        default=ESTADO_ABERTA
    )

    encaminhado_para = models.CharField(
        max_length=25,
        choices=ENCAMINHAMENTO_CHOICES,
        blank=True
    )

    observacoes_resolucao = models.TextField(
        blank=True
    )

    registada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+'
    )

    registada_em = models.DateTimeField(
        auto_now_add=True
    )

    encaminhada_em = models.DateTimeField(
        null=True,
        blank=True
    )

    resolvida_em = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-registada_em']
        verbose_name = 'Reclamação'
        verbose_name_plural = 'Reclamações'

    def __str__(self):
        return f"Reclamação de {self.encarregado} - {self.get_estado_display()}"

    def encaminhar(self, destino):
        self.estado = self.ESTADO_ENCAMINHADA
        self.encaminhado_para = destino
        self.encaminhada_em = timezone.now()
        self.save()

    def resolver(self, observacoes):
        self.estado = self.ESTADO_RESOLVIDA
        self.observacoes_resolucao = observacoes
        self.resolvida_em = timezone.now()
        self.save()
