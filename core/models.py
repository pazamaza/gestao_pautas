from django.db import models


class Escola(models.Model):

    ministerio = models.CharField(
        max_length=150,
        default='Ministério da Educação'
    )

    governo_provincial = models.CharField(
        max_length=150,
        blank=True
    )

    administracao_municipal = models.CharField(
        max_length=150,
        blank=True
    )

    nome = models.CharField(
        max_length=200,
        verbose_name='Nome do complexo escolar'
    )

    logotipo = models.ImageField(
        upload_to='escola/',
        blank=True,
        null=True
    )

    nome_autoridade_visto = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Nome da autoridade (visto)'
    )

    cargo_autoridade_visto = models.CharField(
        max_length=100,
        blank=True,
        default='Directora Municipal',
        verbose_name='Cargo da autoridade (visto)'
    )

    localidade = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Localidade',
        help_text='Ex.: Calumbo — usada na linha de data/assinatura da pauta final.'
    )

    nome_subdirector_pedagogico = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Nome do Subdirector Pedagógico',
        help_text='Assinatura do rodapé da pauta final ("O SUBDIRECTOR PEDAGÓGICO").'
    )

    provincia = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Província',
        help_text='Ex.: Icolo e Bengo — usada no fecho do certificado ("em ..., aos ...").'
    )

    decreto_criacao = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Decreto de criação da escola',
        help_text='Ex.: 307/22 de 21 de 04 — usado no texto do certificado.'
    )

    livro_registo_certificado = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Livro de registo do certificado',
        help_text='Ex.: nº 44, folha - A.'
    )

    base_legal_certificado = models.CharField(
        max_length=250,
        blank=True,
        verbose_name='Base legal do certificado',
        help_text='Ex.: alínea c) do artigo nº 109º da LBSEE nº 17/16, de 7 de Outubro.'
    )

    class Meta:
        verbose_name = 'Escola'
        verbose_name_plural = 'Escola (configuração institucional)'

    def __str__(self):
        return self.nome

    @classmethod
    def obter_configuracao(cls):
        return cls.objects.first()
