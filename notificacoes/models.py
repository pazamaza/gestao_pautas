from django.contrib.auth.models import User
from django.db import models


class Notificacao(models.Model):

    NIVEL_INFO = 'info'
    NIVEL_AVISO = 'aviso'
    NIVEL_ERRO = 'erro'

    NIVEL_CHOICES = [
        (NIVEL_INFO, 'Informação'),
        (NIVEL_AVISO, 'Aviso'),
        (NIVEL_ERRO, 'Erro'),
    ]

    destinatario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notificacoes'
    )

    titulo = models.CharField(
        max_length=150
    )

    mensagem = models.TextField()

    nivel = models.CharField(
        max_length=10,
        choices=NIVEL_CHOICES,
        default=NIVEL_INFO
    )

    link_url = models.CharField(
        max_length=255,
        blank=True
    )

    lida = models.BooleanField(
        default=False
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'

    def __str__(self):
        return f"{self.titulo} - {self.destinatario}"
