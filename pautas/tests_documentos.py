"""Testes do fluxo de Pedidos de Documentos: a Secretaria passa a ser a
única a autorizar/recusar pedidos e a emitir o documento (indicando a forma
de pagamento); quem decidia por tipo antes (Diretor Geral/Sub-diretor/
Diretor de Turma) passa a autenticar o documento já emitido, antes da
Secretaria notificar o aluno para levantamento."""

import datetime

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from alunos.models import Aluno, Encarregado
from professores.models import DiretorTurma, Professor
from turmas.models import AnoLetivo, Classe, Turma

from .models import PedidoDocumento
from .views_documentos import _pode_autenticar_pedido


class PedidoDocumentoTestBase(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Sub-diretor Pedagógico')
        Group.objects.get_or_create(name='Diretor Geral do Complexo')
        Group.objects.get_or_create(name='Chefe de Secretaria')
        grupo_professor, _ = Group.objects.get_or_create(name='Professor')

        self.ano_letivo = AnoLetivo.objects.create(descricao='2026')
        self.classe = Classe.objects.create(nome='Iº')
        self.turma = Turma.objects.create(nome='A', classe=self.classe, ano_letivo=self.ano_letivo)

        encarregado_user = User.objects.create_user(username='enc_doc', password='senha123')
        encarregado = Encarregado.objects.create(user=encarregado_user, telefone='900000000')
        aluno_user = User.objects.create_user(username='aluno_doc', password='senha123')
        self.aluno = Aluno.objects.create(
            user=aluno_user,
            nome='Aluno Documentos',
            numero_processo='NPDOC01',
            data_nascimento=datetime.date(2008, 1, 1),
            sexo='M',
            turma=self.turma,
            encarregado=encarregado,
        )

        self.sub_diretor = User.objects.create_user(username='subdir', password='senha123')
        self.sub_diretor.groups.add(Group.objects.get(name='Sub-diretor Pedagógico'))

        self.diretor_geral = User.objects.create_user(username='dirgeral', password='senha123')
        self.diretor_geral.groups.add(Group.objects.get(name='Diretor Geral do Complexo'))

        self.secretaria = User.objects.create_user(username='secretaria', password='senha123')
        self.secretaria.groups.add(Group.objects.get(name='Chefe de Secretaria'))

        professor_user = User.objects.create_user(username='diretor_turma', password='senha123')
        professor_user.groups.add(grupo_professor)
        self.professor = Professor.objects.create(user=professor_user, numero_funcionario='P900')
        DiretorTurma.objects.create(professor=self.professor, turma=self.turma, ano_letivo=self.ano_letivo)

    def _pedido(self, tipo, status=None):
        pedido = PedidoDocumento.objects.create(aluno=self.aluno, tipo=tipo, ano_letivo=self.ano_letivo)
        if status:
            pedido.status = status
            pedido.save()
        return pedido


class PodeAutenticarPedidoTests(PedidoDocumentoTestBase):
    def test_certificado_so_diretor_geral_autentica(self):
        pedido = self._pedido(PedidoDocumento.TIPO_CERTIFICADO)
        self.assertTrue(_pode_autenticar_pedido(self.diretor_geral, pedido))
        self.assertFalse(_pode_autenticar_pedido(self.sub_diretor, pedido))
        self.assertFalse(_pode_autenticar_pedido(self.secretaria, pedido))

    def test_declaracao_so_subdiretor_autentica(self):
        pedido = self._pedido(PedidoDocumento.TIPO_DECLARACAO)
        self.assertTrue(_pode_autenticar_pedido(self.sub_diretor, pedido))
        self.assertFalse(_pode_autenticar_pedido(self.diretor_geral, pedido))
        self.assertFalse(_pode_autenticar_pedido(self.secretaria, pedido))

    def test_boletim_subdiretor_ou_diretor_turma_autenticam(self):
        pedido = self._pedido(PedidoDocumento.TIPO_BOLETIM)
        self.assertTrue(_pode_autenticar_pedido(self.sub_diretor, pedido))
        self.assertTrue(_pode_autenticar_pedido(self.professor.user, pedido))
        self.assertFalse(_pode_autenticar_pedido(self.diretor_geral, pedido))
        self.assertFalse(_pode_autenticar_pedido(self.secretaria, pedido))


class FilaDocumentosViewTests(PedidoDocumentoTestBase):
    def test_secretaria_ve_fila_completa(self):
        self._pedido(PedidoDocumento.TIPO_BOLETIM)
        self._pedido(PedidoDocumento.TIPO_DECLARACAO)
        self._pedido(PedidoDocumento.TIPO_CERTIFICADO)

        self.client.login(username='secretaria', password='senha123')
        response = self.client.get(reverse('pedidos_documentos_pendentes'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['pedidos']), 3)

    def test_professor_comum_ja_nao_decide_pendentes(self):
        # A decisão de autorizar passou a ser só da Secretaria — um
        # professor comum (mesmo sendo Diretor de Turma) já não acede à
        # fila de pedidos pendentes de autorização.
        self._pedido(PedidoDocumento.TIPO_BOLETIM)

        self.client.login(username='diretor_turma', password='senha123')
        response = self.client.get(reverse('pedidos_documentos_pendentes'))

        self.assertEqual(response.status_code, 403)

    def test_secretaria_autoriza_qualquer_tipo_sozinha(self):
        pedido = self._pedido(PedidoDocumento.TIPO_CERTIFICADO)

        self.client.login(username='secretaria', password='senha123')
        response = self.client.post(
            reverse('pedido_autorizar', args=[pedido.pk]),
            {'forma_pagamento': 'Transferência GPS/Ruper'},
        )

        self.assertRedirects(response, reverse('pedidos_documentos_pendentes'))
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, PedidoDocumento.STATUS_AUTORIZADO)
        self.assertEqual(pedido.forma_pagamento, 'Transferência GPS/Ruper')

    def test_diretor_geral_ja_nao_autoriza_pedidos(self):
        # A autorização (com a nota de pagamento) passou a ser só da
        # Secretaria; o Diretor Geral só entra mais tarde, a autenticar.
        pedido = self._pedido(PedidoDocumento.TIPO_CERTIFICADO)

        self.client.login(username='dirgeral', password='senha123')
        response = self.client.post(
            reverse('pedido_autorizar', args=[pedido.pk]),
            {'forma_pagamento': 'Transferência GPS/Ruper'},
        )

        self.assertEqual(response.status_code, 403)


class PagamentosSecretariaTests(PedidoDocumentoTestBase):
    def test_secretaria_acede_pagamentos(self):
        self.client.login(username='secretaria', password='senha123')
        response = self.client.get(reverse('pedidos_pagamento'))
        self.assertEqual(response.status_code, 200)

    def test_subdiretor_deixou_de_aceder_pagamentos(self):
        # Responsabilidade movida integralmente para a Secretaria (Fase 1).
        self.client.login(username='subdir', password='senha123')
        response = self.client.get(reverse('pedidos_pagamento'))
        self.assertEqual(response.status_code, 403)

    def test_secretaria_confirma_pagamento(self):
        pedido = self._pedido(
            PedidoDocumento.TIPO_DECLARACAO, status=PedidoDocumento.STATUS_PAGAMENTO_SUBMETIDO
        )

        self.client.login(username='secretaria', password='senha123')
        response = self.client.post(reverse('pedido_confirmar_pagamento', args=[pedido.pk]))

        self.assertRedirects(response, reverse('pedidos_pagamento'))
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, PedidoDocumento.STATUS_PAGAMENTO_CONFIRMADO)


class EmissaoAutenticacaoNotificacaoTests(PedidoDocumentoTestBase):
    def test_secretaria_emite_documento(self):
        pedido = self._pedido(
            PedidoDocumento.TIPO_DECLARACAO, status=PedidoDocumento.STATUS_PAGAMENTO_CONFIRMADO
        )

        self.client.login(username='secretaria', password='senha123')
        response = self.client.post(reverse('pedido_emitir', args=[pedido.pk]))

        self.assertRedirects(response, reverse('pedidos_pagamento'))
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, PedidoDocumento.STATUS_EMITIDO)
        self.assertEqual(pedido.emitido_por, self.secretaria)

    def test_diretor_turma_autentica_boletim_emitido(self):
        pedido = self._pedido(PedidoDocumento.TIPO_BOLETIM, status=PedidoDocumento.STATUS_EMITIDO)

        self.client.login(username='diretor_turma', password='senha123')
        response = self.client.post(reverse('pedido_autenticar', args=[pedido.pk]))

        self.assertRedirects(response, reverse('pedidos_autenticacao'))
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, PedidoDocumento.STATUS_AUTENTICADO)
        self.assertEqual(pedido.autenticado_por, self.professor.user)

    def test_secretaria_nao_autentica(self):
        pedido = self._pedido(PedidoDocumento.TIPO_BOLETIM, status=PedidoDocumento.STATUS_EMITIDO)

        self.client.login(username='secretaria', password='senha123')
        response = self.client.post(reverse('pedido_autenticar', args=[pedido.pk]))

        self.assertEqual(response.status_code, 403)

    def test_secretaria_notifica_aluno_apos_autenticacao(self):
        pedido = self._pedido(
            PedidoDocumento.TIPO_BOLETIM, status=PedidoDocumento.STATUS_AUTENTICADO
        )

        self.client.login(username='secretaria', password='senha123')
        response = self.client.post(reverse('pedido_notificar_aluno', args=[pedido.pk]))

        self.assertRedirects(response, reverse('pedidos_pagamento'))
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, PedidoDocumento.STATUS_PRONTO)

    def test_fluxo_completo_ate_pronto(self):
        pedido = self._pedido(PedidoDocumento.TIPO_DECLARACAO)

        self.client.login(username='secretaria', password='senha123')
        self.client.post(
            reverse('pedido_autorizar', args=[pedido.pk]),
            {'forma_pagamento': 'Numerário na Secretaria'},
        )
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, PedidoDocumento.STATUS_AUTORIZADO)

        pedido.status = PedidoDocumento.STATUS_PAGAMENTO_SUBMETIDO
        pedido.save()
        self.client.post(reverse('pedido_confirmar_pagamento', args=[pedido.pk]))
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, PedidoDocumento.STATUS_PAGAMENTO_CONFIRMADO)

        self.client.post(reverse('pedido_emitir', args=[pedido.pk]))
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, PedidoDocumento.STATUS_EMITIDO)

        self.client.logout()
        self.client.login(username='subdir', password='senha123')
        self.client.post(reverse('pedido_autenticar', args=[pedido.pk]))
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, PedidoDocumento.STATUS_AUTENTICADO)

        self.client.logout()
        self.client.login(username='secretaria', password='senha123')
        self.client.post(reverse('pedido_notificar_aluno', args=[pedido.pk]))
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, PedidoDocumento.STATUS_PRONTO)
