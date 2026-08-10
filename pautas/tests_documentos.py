"""Testes da Fase 1 do plano de distribuição de responsabilidades: a
Secretaria passa a ser o ponto único de entrada de pedidos de documentos e
pagamentos, e a decisão de mérito passa a variar por tipo (Boletim ->
Sub-diretor/Diretor de Turma, Declaração -> Sub-diretor, Certificado ->
Diretor Geral)."""

import datetime

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from alunos.models import Aluno, Encarregado
from professores.models import DiretorTurma, Professor
from turmas.models import AnoLetivo, Classe, Turma

from .models import PedidoDocumento
from .views_documentos import _pode_decidir_pedido


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
        self.aluno = Aluno.objects.create(
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

    def _pedido(self, tipo):
        return PedidoDocumento.objects.create(aluno=self.aluno, tipo=tipo, ano_letivo=self.ano_letivo)


class PodeDecidirPedidoTests(PedidoDocumentoTestBase):
    def test_certificado_so_diretor_geral_decide(self):
        pedido = self._pedido(PedidoDocumento.TIPO_CERTIFICADO)
        self.assertTrue(_pode_decidir_pedido(self.diretor_geral, pedido))
        self.assertFalse(_pode_decidir_pedido(self.sub_diretor, pedido))
        self.assertFalse(_pode_decidir_pedido(self.secretaria, pedido))

    def test_declaracao_so_subdiretor_decide(self):
        pedido = self._pedido(PedidoDocumento.TIPO_DECLARACAO)
        self.assertTrue(_pode_decidir_pedido(self.sub_diretor, pedido))
        self.assertFalse(_pode_decidir_pedido(self.diretor_geral, pedido))
        self.assertFalse(_pode_decidir_pedido(self.secretaria, pedido))

    def test_boletim_subdiretor_ou_diretor_turma_decidem(self):
        pedido = self._pedido(PedidoDocumento.TIPO_BOLETIM)
        self.assertTrue(_pode_decidir_pedido(self.sub_diretor, pedido))
        self.assertTrue(_pode_decidir_pedido(self.professor.user, pedido))
        self.assertFalse(_pode_decidir_pedido(self.diretor_geral, pedido))
        self.assertFalse(_pode_decidir_pedido(self.secretaria, pedido))


class FilaDocumentosViewTests(PedidoDocumentoTestBase):
    def test_secretaria_ve_fila_completa(self):
        self._pedido(PedidoDocumento.TIPO_BOLETIM)
        self._pedido(PedidoDocumento.TIPO_DECLARACAO)
        self._pedido(PedidoDocumento.TIPO_CERTIFICADO)

        self.client.login(username='secretaria', password='senha123')
        response = self.client.get(reverse('pedidos_documentos_pendentes'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['pedidos']), 3)

    def test_professor_comum_ve_so_boletins_da_sua_turma(self):
        self._pedido(PedidoDocumento.TIPO_BOLETIM)
        self._pedido(PedidoDocumento.TIPO_DECLARACAO)
        self._pedido(PedidoDocumento.TIPO_CERTIFICADO)

        self.client.login(username='diretor_turma', password='senha123')
        response = self.client.get(reverse('pedidos_documentos_pendentes'))

        self.assertEqual(response.status_code, 200)
        pedidos = response.context['pedidos']
        self.assertEqual(len(pedidos), 1)
        self.assertEqual(pedidos[0].tipo, PedidoDocumento.TIPO_BOLETIM)

    def test_secretaria_sozinha_nao_pode_autorizar_certificado(self):
        pedido = self._pedido(PedidoDocumento.TIPO_CERTIFICADO)

        self.client.login(username='secretaria', password='senha123')
        response = self.client.post(reverse('pedido_autorizar', args=[pedido.pk]))

        self.assertEqual(response.status_code, 403)

    def test_diretor_geral_autoriza_certificado(self):
        pedido = self._pedido(PedidoDocumento.TIPO_CERTIFICADO)

        self.client.login(username='dirgeral', password='senha123')
        response = self.client.post(reverse('pedido_autorizar', args=[pedido.pk]))

        self.assertRedirects(response, reverse('pedidos_documentos_pendentes'))
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, PedidoDocumento.STATUS_AUTORIZADO)


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
        pedido = self._pedido(PedidoDocumento.TIPO_DECLARACAO)
        pedido.status = PedidoDocumento.STATUS_PAGAMENTO_SUBMETIDO
        pedido.save()

        self.client.login(username='secretaria', password='senha123')
        response = self.client.post(reverse('pedido_confirmar_pagamento', args=[pedido.pk]))

        self.assertRedirects(response, reverse('pedidos_pagamento'))
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, PedidoDocumento.STATUS_PRONTO)
