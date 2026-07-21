from datetime import timedelta

from django.db import models
from django.utils import timezone
from alunos.models import Aluno
from professores.models import AtribuicaoDocente

# Nº de dias corridos, a partir da data da falta, em que o encarregado/aluno
# ainda pode submeter uma justificação. Passado este prazo, uma falta 'F'
# sem justificação aprovada torna-se definitivamente injustificada
# (ver Frequencia.esta_injustificada).
PRAZO_JUSTIFICACAO_DIAS = 5


class Frequencia(models.Model):
    # P (Presente) e A (Atraso) contam ambos como presença para efeitos de
    # frequência — ver Aluno.calcular_frequencia() em alunos/models.py, que
    # filtra por estado__in=['P', 'A']. Só F (Falta) conta como ausência.
    PRESENTE = 'P'
    FALTA = 'F'
    JUSTIFICADA = 'J'
    ATRASO = 'A'
    STATUS = [
        (PRESENTE, 'Presente'),
        (FALTA, 'Falta'),
        (JUSTIFICADA, 'Justificada'),
        (ATRASO, 'Atraso'),
    ]

    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    atribuicao = models.ForeignKey(
        AtribuicaoDocente,
        on_delete=models.CASCADE
    )
    data = models.DateField()
    estado = models.CharField(max_length=1, choices=STATUS)
    observacao = models.TextField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('aluno', 'atribuicao', 'data')

    def __str__(self):
        return (f"{self.aluno} - " f"{self.data}")

    def prazo_justificacao_expirado(self):
        """True se já passaram PRAZO_JUSTIFICACAO_DIAS desde a data da falta."""
        limite = self.data + timedelta(days=PRAZO_JUSTIFICACAO_DIAS)
        return timezone.localdate() > limite

    def esta_injustificada(self):
        # Uma falta só é considerada "injustificada" de forma definitiva
        # quando reúne 3 condições: (1) o estado é mesmo 'F' (falta), não
        # 'J'/'A'; (2) o prazo de 5 dias para justificar já expirou — antes
        # disso está apenas "pendente"; (3) não existe uma JustificacaoFalta
        # ligada (relação O2O 'justificacaofalta') com aprovada=True.
        if self.estado != self.FALTA:
            return False
        if not self.prazo_justificacao_expirado():
            return False
        justificacao = getattr(self, 'justificacaofalta', None)
        return not (justificacao and justificacao.aprovada)


class JustificacaoFalta(models.Model):
    frequencia = models.OneToOneField(
        Frequencia,
        on_delete=models.CASCADE
    )
    motivo = models.TextField()
    documento = models.FileField(
        upload_to='justificacoes/',
        blank=True,
        null=True
    )
    data_submissao = models.DateTimeField(auto_now_add=True)

    aprovada = models.BooleanField(default=False)

    def __str__(self):
        return (f"Justificação - " f"{self.frequencia.aluno}")