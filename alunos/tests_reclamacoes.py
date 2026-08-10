"""Testes da Fase 2 do plano de distribuição de responsabilidades:
Reclamacao (Coordenador de Pais e Encarregados de Educação regista e
encaminha; Diretor Geral/Sub-diretor Pedagógico resolvem o que lhes for
encaminhado)."""

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .models import Encarregado, Reclamacao


class ReclamacaoTestBase(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Diretor Geral do Complexo')
        Group.objects.get_or_create(name='Sub-diretor Pedagógico')
        grupo_coord_pais, _ = Group.objects.get_or_create(
            name='Coordenador de Pais e Encarregados de Educação'
        )

        self.coordenador = User.objects.create_user(username='coord_pais', password='senha123')
        self.coordenador.groups.add(grupo_coord_pais)

        self.diretor_geral = User.objects.create_user(username='dg_reclamacao', password='senha123')
        self.diretor_geral.groups.add(Group.objects.get(name='Diretor Geral do Complexo'))

        self.sub_diretor = User.objects.create_user(username='sd_reclamacao', password='senha123')
        self.sub_diretor.groups.add(Group.objects.get(name='Sub-diretor Pedagógico'))

        encarregado_user = User.objects.create_user(username='enc_reclamacao', password='senha123')
        self.encarregado = Encarregado.objects.create(user=encarregado_user, telefone='900111222')

    def _reclamacao(self, **kwargs):
        return Reclamacao.objects.create(encarregado=self.encarregado, motivo='Motivo teste', **kwargs)


class ReclamacaoModeloTests(ReclamacaoTestBase):
    def test_encaminhar_muda_estado_e_destino(self):
        reclamacao = self._reclamacao()
        reclamacao.encaminhar(Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL)

        self.assertEqual(reclamacao.estado, Reclamacao.ESTADO_ENCAMINHADA)
        self.assertEqual(reclamacao.encaminhado_para, Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL)
        self.assertIsNotNone(reclamacao.encaminhada_em)

    def test_resolver_muda_estado_e_grava_observacoes(self):
        reclamacao = self._reclamacao()
        reclamacao.resolver('Assunto esclarecido por telefone.')

        self.assertEqual(reclamacao.estado, Reclamacao.ESTADO_RESOLVIDA)
        self.assertEqual(reclamacao.observacoes_resolucao, 'Assunto esclarecido por telefone.')
        self.assertIsNotNone(reclamacao.resolvida_em)


class ReclamacaoViewsTests(ReclamacaoTestBase):
    def test_coordenador_pais_regista_reclamacao(self):
        self.client.login(username='coord_pais', password='senha123')
        response = self.client.post(reverse('reclamacao_nova'), {
            'encarregado': self.encarregado.pk,
            'motivo': 'O meu educando não recebeu o boletim.',
        })

        self.assertRedirects(response, reverse('reclamacao_lista'))
        reclamacao = Reclamacao.objects.get()
        self.assertEqual(reclamacao.registada_por, self.coordenador)

    def test_diretor_geral_nao_pode_registar_reclamacao(self):
        self.client.login(username='dg_reclamacao', password='senha123')
        response = self.client.get(reverse('reclamacao_nova'))
        self.assertEqual(response.status_code, 403)

    def test_diretor_geral_so_ve_reclamacoes_encaminhadas_para_si(self):
        aberta = self._reclamacao()
        para_dg = self._reclamacao()
        para_dg.encaminhar(Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL)
        para_sd = self._reclamacao()
        para_sd.encaminhar(Reclamacao.ENCAMINHAMENTO_SUBDIRETOR_PEDAGOGICO)

        self.client.login(username='dg_reclamacao', password='senha123')
        response = self.client.get(reverse('reclamacao_lista'))

        ids_visiveis = {r.pk for r in response.context['reclamacoes']}
        self.assertEqual(ids_visiveis, {para_dg.pk})

    def test_coordenador_pais_ve_todas(self):
        aberta = self._reclamacao()
        para_dg = self._reclamacao()
        para_dg.encaminhar(Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL)

        self.client.login(username='coord_pais', password='senha123')
        response = self.client.get(reverse('reclamacao_lista'))

        ids_visiveis = {r.pk for r in response.context['reclamacoes']}
        self.assertEqual(ids_visiveis, {aberta.pk, para_dg.pk})

    def test_diretor_geral_resolve_reclamacao_encaminhada_para_si(self):
        reclamacao = self._reclamacao()
        reclamacao.encaminhar(Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL)

        self.client.login(username='dg_reclamacao', password='senha123')
        response = self.client.post(
            reverse('reclamacao_resolver', args=[reclamacao.pk]),
            {'observacoes_resolucao': 'Resolvido em reunião.'},
        )

        self.assertRedirects(response, reverse('reclamacao_detalhe', args=[reclamacao.pk]))
        reclamacao.refresh_from_db()
        self.assertEqual(reclamacao.estado, Reclamacao.ESTADO_RESOLVIDA)

    def test_sub_diretor_nao_resolve_reclamacao_encaminhada_ao_diretor_geral(self):
        # 404, não 403: a reclamação nem sequer está no âmbito visível do
        # Sub-diretor (_reclamacoes_visiveis), o que evita confirmar a
        # existência de uma reclamação fora do seu escopo.
        reclamacao = self._reclamacao()
        reclamacao.encaminhar(Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL)

        self.client.login(username='sd_reclamacao', password='senha123')
        response = self.client.post(
            reverse('reclamacao_resolver', args=[reclamacao.pk]),
            {'observacoes_resolucao': 'Tentativa indevida.'},
        )

        self.assertEqual(response.status_code, 404)
        reclamacao.refresh_from_db()
        self.assertEqual(reclamacao.estado, Reclamacao.ESTADO_ENCAMINHADA)
