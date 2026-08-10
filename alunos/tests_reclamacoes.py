"""Testes da Reclamacao, incluindo o redesenho da Fase 5: cadeia de
encaminhamento em 4 saltos (Coordenador de Pais -> Secretaria -> Diretor
Geral -> Sub-diretor Pedagógico / Diretor de Turma), com notificação a
cada salto e, na resolução, notificação direta ao encarregado."""

import datetime

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from notificacoes.models import Notificacao
from professores.models import DiretorTurma, Professor
from turmas.models import AnoLetivo, Classe, Turma

from .models import Aluno, Encarregado, Reclamacao


class ReclamacaoTestBase(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Diretor Geral do Complexo')
        Group.objects.get_or_create(name='Sub-diretor Pedagógico')
        Group.objects.get_or_create(name='Chefe de Secretaria')
        grupo_coord_pais, _ = Group.objects.get_or_create(
            name='Coordenador de Pais e Encarregados de Educação'
        )
        grupo_professor, _ = Group.objects.get_or_create(name='Professor')

        self.coordenador = User.objects.create_user(username='coord_pais', password='senha123')
        self.coordenador.groups.add(grupo_coord_pais)

        self.secretaria = User.objects.create_user(username='secretaria_rec', password='senha123')
        self.secretaria.groups.add(Group.objects.get(name='Chefe de Secretaria'))

        self.diretor_geral = User.objects.create_user(username='dg_reclamacao', password='senha123')
        self.diretor_geral.groups.add(Group.objects.get(name='Diretor Geral do Complexo'))

        self.sub_diretor = User.objects.create_user(username='sd_reclamacao', password='senha123')
        self.sub_diretor.groups.add(Group.objects.get(name='Sub-diretor Pedagógico'))

        ano_letivo = AnoLetivo.objects.create(descricao='2026')
        classe, _ = Classe.objects.get_or_create(nome='7ª Classe')
        self.turma = Turma.objects.create(nome='A', classe=classe, ano_letivo=ano_letivo)

        diretor_turma_user = User.objects.create_user(username='dt_reclamacao', password='senha123')
        diretor_turma_user.groups.add(grupo_professor)
        professor = Professor.objects.create(user=diretor_turma_user, numero_funcionario='PR900')
        DiretorTurma.objects.create(professor=professor, turma=self.turma, ano_letivo=ano_letivo)

        encarregado_user = User.objects.create_user(username='enc_reclamacao', password='senha123')
        self.encarregado = Encarregado.objects.create(user=encarregado_user, telefone='900111222')

        self.aluno = Aluno.objects.create(
            nome='Aluno Reclamação', numero_processo='NPREC01',
            data_nascimento=datetime.date(2010, 1, 1), sexo='M',
            turma=self.turma, encarregado=self.encarregado,
        )

    def _reclamacao(self, **kwargs):
        return Reclamacao.objects.create(encarregado=self.encarregado, motivo='Motivo teste', **kwargs)


class ReclamacaoModeloTests(ReclamacaoTestBase):
    def test_encaminhar_muda_estado_e_destino(self):
        reclamacao = self._reclamacao()
        reclamacao.encaminhar(Reclamacao.ENCAMINHAMENTO_SECRETARIA)

        self.assertEqual(reclamacao.estado, Reclamacao.ESTADO_ENCAMINHADA)
        self.assertEqual(reclamacao.encaminhado_para, Reclamacao.ENCAMINHAMENTO_SECRETARIA)
        self.assertIsNotNone(reclamacao.encaminhada_em)

    def test_resolver_muda_estado_e_grava_observacoes(self):
        reclamacao = self._reclamacao()
        reclamacao.resolver('Assunto esclarecido por telefone.')

        self.assertEqual(reclamacao.estado, Reclamacao.ESTADO_RESOLVIDA)
        self.assertEqual(reclamacao.observacoes_resolucao, 'Assunto esclarecido por telefone.')
        self.assertIsNotNone(reclamacao.resolvida_em)

    def test_esta_atrasada_apos_prazo_sem_movimento(self):
        reclamacao = self._reclamacao()
        Reclamacao.objects.filter(pk=reclamacao.pk).update(
            registada_em=timezone.now() - datetime.timedelta(days=4)
        )
        reclamacao.refresh_from_db()
        self.assertTrue(reclamacao.esta_atrasada)

    def test_nao_esta_atrasada_dentro_do_prazo(self):
        reclamacao = self._reclamacao()
        self.assertFalse(reclamacao.esta_atrasada)

    def test_resolvida_nunca_esta_atrasada(self):
        reclamacao = self._reclamacao()
        Reclamacao.objects.filter(pk=reclamacao.pk).update(
            registada_em=timezone.now() - datetime.timedelta(days=10)
        )
        reclamacao.refresh_from_db()
        reclamacao.resolver('Feito.')
        self.assertFalse(reclamacao.esta_atrasada)


class FluxoCompletoReclamacaoTests(ReclamacaoTestBase):
    """Percorre a cadeia completa: Coordenador -> Secretaria -> Diretor
    Geral -> Sub-diretor Pedagógico (assunto de notas), com notificação a
    cada salto e ao encarregado na resolução."""

    def test_cadeia_completa_ate_subdiretor(self):
        self.client.login(username='coord_pais', password='senha123')
        response = self.client.post(reverse('reclamacao_nova'), {
            'encarregado': self.encarregado.pk,
            'motivo': 'Discordância com uma nota lançada.',
        })
        self.assertRedirects(response, reverse('reclamacao_lista'))
        reclamacao = Reclamacao.objects.get()
        self.assertEqual(reclamacao.estado, Reclamacao.ESTADO_ABERTA)

        # Coordenador encaminha à Secretaria.
        self.client.post(reverse('reclamacao_encaminhar', args=[reclamacao.pk]), {
            'encaminhado_para': Reclamacao.ENCAMINHAMENTO_SECRETARIA,
        })
        reclamacao.refresh_from_db()
        self.assertEqual(reclamacao.encaminhado_para, Reclamacao.ENCAMINHAMENTO_SECRETARIA)
        self.assertTrue(
            Notificacao.objects.filter(destinatario=self.secretaria).exists()
        )

        # Secretaria encaminha ao Diretor Geral.
        self.client.login(username='secretaria_rec', password='senha123')
        self.client.post(reverse('reclamacao_encaminhar', args=[reclamacao.pk]), {
            'encaminhado_para': Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL,
        })
        reclamacao.refresh_from_db()
        self.assertEqual(reclamacao.encaminhado_para, Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL)
        self.assertTrue(
            Notificacao.objects.filter(destinatario=self.diretor_geral).exists()
        )

        # Diretor Geral encaminha ao Sub-diretor (assunto de notas/pautas).
        self.client.login(username='dg_reclamacao', password='senha123')
        self.client.post(reverse('reclamacao_encaminhar', args=[reclamacao.pk]), {
            'encaminhado_para': Reclamacao.ENCAMINHAMENTO_SUBDIRETOR_PEDAGOGICO,
        })
        reclamacao.refresh_from_db()
        self.assertEqual(reclamacao.encaminhado_para, Reclamacao.ENCAMINHAMENTO_SUBDIRETOR_PEDAGOGICO)

        # Sub-diretor resolve -> notifica Coordenador de Pais e o encarregado.
        self.client.login(username='sd_reclamacao', password='senha123')
        response = self.client.post(reverse('reclamacao_resolver', args=[reclamacao.pk]), {
            'observacoes_resolucao': 'Nota corrigida.',
        })
        self.assertRedirects(response, reverse('reclamacao_detalhe', args=[reclamacao.pk]))
        reclamacao.refresh_from_db()
        self.assertEqual(reclamacao.estado, Reclamacao.ESTADO_RESOLVIDA)

        self.assertTrue(Notificacao.objects.filter(destinatario=self.coordenador).exists())
        self.assertTrue(
            Notificacao.objects.filter(destinatario=self.encarregado.user).exists()
        )

    def test_diretor_geral_encaminha_ao_diretor_de_turma(self):
        reclamacao = self._reclamacao(aluno=self.aluno)
        reclamacao.encaminhar(Reclamacao.ENCAMINHAMENTO_SECRETARIA)
        reclamacao.encaminhar(Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL)

        self.client.login(username='dg_reclamacao', password='senha123')
        response = self.client.post(reverse('reclamacao_encaminhar', args=[reclamacao.pk]), {
            'encaminhado_para': Reclamacao.ENCAMINHAMENTO_DIRETOR_TURMA,
        })
        self.assertRedirects(response, reverse('reclamacao_detalhe', args=[reclamacao.pk]))
        reclamacao.refresh_from_db()
        self.assertEqual(reclamacao.encaminhado_para, Reclamacao.ENCAMINHAMENTO_DIRETOR_TURMA)

        self.client.login(username='dt_reclamacao', password='senha123')
        response = self.client.post(reverse('reclamacao_resolver', args=[reclamacao.pk]), {
            'observacoes_resolucao': 'Falta justificada, esclarecido com o encarregado.',
        })
        self.assertRedirects(response, reverse('reclamacao_detalhe', args=[reclamacao.pk]))
        reclamacao.refresh_from_db()
        self.assertEqual(reclamacao.estado, Reclamacao.ESTADO_RESOLVIDA)

    def test_diretor_geral_resolve_diretamente_outro_assunto(self):
        reclamacao = self._reclamacao()
        reclamacao.encaminhar(Reclamacao.ENCAMINHAMENTO_SECRETARIA)
        reclamacao.encaminhar(Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL)

        self.client.login(username='dg_reclamacao', password='senha123')
        response = self.client.post(reverse('reclamacao_resolver', args=[reclamacao.pk]), {
            'observacoes_resolucao': 'Assunto tratado diretamente.',
        })
        self.assertRedirects(response, reverse('reclamacao_detalhe', args=[reclamacao.pk]))
        reclamacao.refresh_from_db()
        self.assertEqual(reclamacao.estado, Reclamacao.ESTADO_RESOLVIDA)


class PermissaoPorSaltoTests(ReclamacaoTestBase):
    def test_secretaria_nao_pode_encaminhar_reclamacao_ainda_aberta(self):
        # 404: uma reclamação "aberta" nem está no âmbito visível da
        # Secretaria (_reclamacoes_visiveis exclui ESTADO_ABERTA para ela).
        reclamacao = self._reclamacao()
        self.client.login(username='secretaria_rec', password='senha123')
        response = self.client.post(reverse('reclamacao_encaminhar', args=[reclamacao.pk]), {
            'encaminhado_para': Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL,
        })
        self.assertEqual(response.status_code, 404)

    def test_diretor_geral_nao_pode_encaminhar_antes_de_chegar_a_secretaria(self):
        # 404: enquanto está só na Secretaria, ainda não é visível para o
        # Diretor Geral (_reclamacoes_visiveis só mostra a partir de si).
        reclamacao = self._reclamacao()
        reclamacao.encaminhar(Reclamacao.ENCAMINHAMENTO_SECRETARIA)

        self.client.login(username='dg_reclamacao', password='senha123')
        response = self.client.post(reverse('reclamacao_encaminhar', args=[reclamacao.pk]), {
            'encaminhado_para': Reclamacao.ENCAMINHAMENTO_SUBDIRETOR_PEDAGOGICO,
        })
        self.assertEqual(response.status_code, 404)

    def test_diretor_geral_nao_pode_encaminhar_para_diretor_turma_sem_aluno(self):
        # Sem aluno associado a opção "Diretor de Turma" nem aparece entre
        # os destinos possíveis; o formulário rejeita o valor (não é uma
        # choice válida) e a reclamação fica como estava.
        reclamacao = self._reclamacao()  # sem aluno associado
        reclamacao.encaminhar(Reclamacao.ENCAMINHAMENTO_SECRETARIA)
        reclamacao.encaminhar(Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL)

        self.client.login(username='dg_reclamacao', password='senha123')
        response = self.client.post(reverse('reclamacao_encaminhar', args=[reclamacao.pk]), {
            'encaminhado_para': Reclamacao.ENCAMINHAMENTO_DIRETOR_TURMA,
        })
        self.assertRedirects(response, reverse('reclamacao_detalhe', args=[reclamacao.pk]))
        reclamacao.refresh_from_db()
        self.assertEqual(reclamacao.encaminhado_para, Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL)

    def test_diretor_geral_nao_pode_registar_reclamacao(self):
        self.client.login(username='dg_reclamacao', password='senha123')
        response = self.client.get(reverse('reclamacao_nova'))
        self.assertEqual(response.status_code, 403)


class VisibilidadeReclamacaoTests(ReclamacaoTestBase):
    def test_coordenador_pais_ve_todas(self):
        aberta = self._reclamacao()
        na_secretaria = self._reclamacao()
        na_secretaria.encaminhar(Reclamacao.ENCAMINHAMENTO_SECRETARIA)

        self.client.login(username='coord_pais', password='senha123')
        response = self.client.get(reverse('reclamacao_lista'))

        ids_visiveis = {r.pk for r in response.context['reclamacoes']}
        self.assertEqual(ids_visiveis, {aberta.pk, na_secretaria.pk})

    def test_secretaria_nao_ve_reclamacao_ainda_aberta(self):
        aberta = self._reclamacao()
        self.client.login(username='secretaria_rec', password='senha123')
        response = self.client.get(reverse('reclamacao_lista'))

        ids_visiveis = {r.pk for r in response.context['reclamacoes']}
        self.assertNotIn(aberta.pk, ids_visiveis)

    def test_diretor_geral_ve_toda_a_cadeia_a_partir_de_si(self):
        para_dg = self._reclamacao()
        para_dg.encaminhar(Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL)
        para_sd = self._reclamacao()
        para_sd.encaminhar(Reclamacao.ENCAMINHAMENTO_SUBDIRETOR_PEDAGOGICO)
        na_secretaria = self._reclamacao()
        na_secretaria.encaminhar(Reclamacao.ENCAMINHAMENTO_SECRETARIA)

        self.client.login(username='dg_reclamacao', password='senha123')
        response = self.client.get(reverse('reclamacao_lista'))

        ids_visiveis = {r.pk for r in response.context['reclamacoes']}
        self.assertEqual(ids_visiveis, {para_dg.pk, para_sd.pk})
