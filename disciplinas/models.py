from django.db import models


class Disciplina(models.Model):

    nome = models.CharField(
        max_length=100,
        unique=True
    )

    sigla = models.CharField(
        max_length=10,
        unique=True
    )

    descricao = models.TextField(
        blank=True,
        null=True
    )

    ativa = models.BooleanField(
        default=True
    )

    nuclear = models.BooleanField(
        default=False,
        verbose_name='Disciplina nuclear',
        help_text='Disciplinas nucleares (Matemática, Língua Portuguesa) não têm direito a recurso.'
    )

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome