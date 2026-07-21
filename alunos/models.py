from datetime import date

from django.db import models
from django.contrib.auth.models import User
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
