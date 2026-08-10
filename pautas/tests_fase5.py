"""Testes da Fase 5 do plano de distribuição de responsabilidades:
homologação da pauta final pelo Diretor Geral, SLA de validação/
homologação e o registo de auditoria."""

import datetime

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from alunos.models import Aluno, Encarregado
from disciplinas.models import Disciplina
from professores.models import AtribuicaoDocente, Professor
from turmas.models import AnoLetivo, Classe, PeriodoAcademico, Turma

from .models import Avaliacao, ResultadoDisciplina


class Fase5TestBase(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Sub-diretor Pedagógico')
        grupo_diretor_geral, _ = Group.objects.get_or_create(name='Diretor Geral do Complexo')

        self.sub_diretor = User.objects.create_user(username='subdir_f5', password='senha123')
        self.sub_diretor.groups.add(Group.objects.get(name='Sub-diretor Pedagógico'))

        self.diretor_geral = User.objects.create_user(username='dg_f5', password='senha123')
        self.diretor_geral.groups.add(grupo_diretor_geral)

        self.ano_letivo = AnoLetivo.objects.create(descricao='2026')
        self.classe, _ = Classe.objects.get_or_create(nome='7ª Classe')
        self.turma = Turma.objects.create(nome='A', classe=self.classe, ano_letivo=self.ano_letivo)
        self.disciplina = Disciplina.objects.create(nome='Matemática', sigla='MAT')
        self.periodo = PeriodoAcademico.objects.create(nome='1º Trimestre', ano_letivo=self.ano_letivo)

        professor_user = User.objects.create_user(username='prof_f5', password='senha123')
        professor = Professor.objects.create(user=professor_user, numero_funcionario='PF500')
        self.atribuicao = AtribuicaoDocente.objects.create(
            professor=professor, disciplina=self.disciplina, turma=self.turma, ano_letivo=self.ano_letivo,
        )

        encarregado_user = User.objects.create_user(username='enc_f5', password='senha123')
        encarregado = Encarregado.objects.create(user=encarregado_user, telefone='900000000')
        self.aluno = Aluno.objects.create(
            nome='Aluno Fase5', numero_processo='NPF5001',
            data_nascimento=datetime.date(2010, 1, 1), sexo='M',
            turma=self.turma, encarregado=encarregado,
        )

        self.resultado = ResultadoDisciplina.objects.create(
            aluno=self.aluno, disciplina=self.disciplina, ano_letivo=self.ano_letivo,
            mt1=12, mt2=13, mt3=14, mf=13,
        )


class HomologacaoModeloTests(Fase5TestBase):
    def test_homologar_grava_quem_e_quando(self):
        self.resultado.marcar_validada(self.sub_diretor)
        self.resultado.homologar(self.diretor_geral)

        self.assertEqual(self.resultado.homologado_por, self.diretor_geral)
        self.assertIsNotNone(self.resultado.homologado_em)

    def test_nao_esta_atrasada_se_nao_validado(self):
        self.assertFalse(self.resultado.esta_atrasada_homologacao)

    def test_esta_atrasada_apos_prazo_sem_homologar(self):
        self.resultado.marcar_validada(self.sub_diretor)
        ResultadoDisciplina.objects.filter(pk=self.resultado.pk).update(
            validado_em=timezone.now() - datetime.timedelta(days=4)
        )
        self.resultado.refresh_from_db()
        self.assertTrue(self.resultado.esta_atrasada_homologacao)

    def test_nao_esta_atrasada_depois_de_homologada(self):
        self.resultado.marcar_validada(self.sub_diretor)
        ResultadoDisciplina.objects.filter(pk=self.resultado.pk).update(
            validado_em=timezone.now() - datetime.timedelta(days=10)
        )
        self.resultado.refresh_from_db()
        self.resultado.homologar(self.diretor_geral)
        self.assertFalse(self.resultado.esta_atrasada_homologacao)


class AvaliacaoSLATests(Fase5TestBase):
    def test_avaliacao_nao_esta_atrasada_dentro_do_prazo(self):
        avaliacao = Avaliacao.objects.create(atribuicao=self.atribuicao, periodo=self.periodo)
        self.assertFalse(avaliacao.esta_atrasada_validacao)

    def test_avaliacao_atrasada_apos_10_dias_sem_validar(self):
        avaliacao = Avaliacao.objects.create(atribuicao=self.atribuicao, periodo=self.periodo)
        Avaliacao.objects.filter(pk=avaliacao.pk).update(
            criado_em=timezone.now() - datetime.timedelta(days=11)
        )
        avaliacao.refresh_from_db()
        self.assertTrue(avaliacao.esta_atrasada_validacao)

    def test_avaliacao_validada_nunca_esta_atrasada(self):
        avaliacao = Avaliacao.objects.create(atribuicao=self.atribuicao, periodo=self.periodo)
        Avaliacao.objects.filter(pk=avaliacao.pk).update(
            criado_em=timezone.now() - datetime.timedelta(days=11)
        )
        avaliacao.refresh_from_db()
        avaliacao.marcar_validada(self.sub_diretor)
        self.assertFalse(avaliacao.esta_atrasada_validacao)


class ResultadoHomologarViewTests(Fase5TestBase):
    def test_diretor_geral_homologa_resultado_validado(self):
        self.resultado.marcar_validada(self.sub_diretor)

        self.client.login(username='dg_f5', password='senha123')
        response = self.client.get(reverse('resultado_homologar', args=[self.resultado.pk]))

        self.assertRedirects(response, reverse('resultado_lista'))
        self.resultado.refresh_from_db()
        self.assertEqual(self.resultado.homologado_por, self.diretor_geral)

    def test_nao_homologa_resultado_ainda_nao_validado(self):
        self.client.login(username='dg_f5', password='senha123')
        response = self.client.get(reverse('resultado_homologar', args=[self.resultado.pk]))

        self.assertRedirects(response, reverse('resultado_lista'))
        self.resultado.refresh_from_db()
        self.assertIsNone(self.resultado.homologado_por)

    def test_subdiretor_nao_pode_homologar(self):
        self.resultado.marcar_validada(self.sub_diretor)

        self.client.login(username='subdir_f5', password='senha123')
        response = self.client.get(reverse('resultado_homologar', args=[self.resultado.pk]))

        self.assertEqual(response.status_code, 403)


class AuditoriaViewTests(Fase5TestBase):
    def test_diretor_geral_acede_a_auditoria(self):
        self.client.login(username='dg_f5', password='senha123')
        response = self.client.get(reverse('auditoria_registo'))
        self.assertEqual(response.status_code, 200)

    def test_subdiretor_nao_acede_a_auditoria(self):
        self.client.login(username='subdir_f5', password='senha123')
        response = self.client.get(reverse('auditoria_registo'))
        self.assertEqual(response.status_code, 403)

    def test_avaliacao_validada_aparece_no_periodo_certo(self):
        avaliacao = Avaliacao.objects.create(atribuicao=self.atribuicao, periodo=self.periodo)
        avaliacao.marcar_validada(self.sub_diretor)

        self.client.login(username='dg_f5', password='senha123')
        response = self.client.get(reverse('auditoria_registo'), {'periodo': self.periodo.pk})

        self.assertEqual(response.status_code, 200)
        ids = {a.pk for a in response.context['avaliacoes']}
        self.assertEqual(ids, {avaliacao.pk})
