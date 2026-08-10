"""Testes da Fase 3 do plano de distribuição de responsabilidades: o
Coordenador de Turno passa a poder registar um parecer numa Justificação
de Falta antes da decisão final, e essa decisão final deixa de poder ser
tomada por "qualquer professor da disciplina" — passa a ser exclusiva do
Sub-diretor Pedagógico ou do Diretor de Turma da turma do aluno."""

import datetime

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from alunos.models import Aluno, Encarregado
from disciplinas.models import Disciplina
from notificacoes.models import Notificacao
from professores.models import AtribuicaoDocente, DiretorTurma, Professor
from turmas.models import AnoLetivo, Classe, Turma

from .models import Frequencia, JustificacaoFalta


class JustificacaoFase3TestBase(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Sub-diretor Pedagógico')
        grupo_professor, _ = Group.objects.get_or_create(name='Professor')
        grupo_coord_turno, _ = Group.objects.get_or_create(name='Coordenador de Turno')

        self.sub_diretor = User.objects.create_user(username='subdir_f3', password='senha123')
        self.sub_diretor.groups.add(Group.objects.get(name='Sub-diretor Pedagógico'))

        self.ano_letivo = AnoLetivo.objects.create(descricao='2026')
        self.classe, _ = Classe.objects.get_or_create(nome='7ª Classe')
        self.turma = Turma.objects.create(
            nome='A', classe=self.classe, ano_letivo=self.ano_letivo, periodo='tarde'
        )
        self.disciplina = Disciplina.objects.create(nome='Matemática', sigla='MAT')

        professor_user = User.objects.create_user(username='prof_f3', password='senha123')
        professor_user.groups.add(grupo_professor)
        self.professor = Professor.objects.create(user=professor_user, numero_funcionario='PF001')

        diretor_turma_user = User.objects.create_user(username='dt_f3', password='senha123')
        diretor_turma_user.groups.add(grupo_professor)
        self.diretor_turma_professor = Professor.objects.create(
            user=diretor_turma_user, numero_funcionario='PF002'
        )
        DiretorTurma.objects.create(
            professor=self.diretor_turma_professor, turma=self.turma, ano_letivo=self.ano_letivo
        )

        self.atribuicao = AtribuicaoDocente.objects.create(
            professor=self.professor, disciplina=self.disciplina,
            turma=self.turma, ano_letivo=self.ano_letivo,
        )

        self.coordenador_turno = User.objects.create_user(username='coord_turno_f3', password='senha123')
        self.coordenador_turno.groups.add(grupo_coord_turno)
        self.coordenador_turno.perfil.turno_coordenado = 'tarde'
        self.coordenador_turno.perfil.save()

        self.coordenador_turno_manha = User.objects.create_user(
            username='coord_turno_manha_f3', password='senha123'
        )
        self.coordenador_turno_manha.groups.add(grupo_coord_turno)
        self.coordenador_turno_manha.perfil.turno_coordenado = 'manha'
        self.coordenador_turno_manha.perfil.save()

        encarregado_user = User.objects.create_user(username='enc_f3', password='senha123')
        encarregado = Encarregado.objects.create(user=encarregado_user, telefone='900000000')
        self.aluno = Aluno.objects.create(
            nome='Aluno Fase3', numero_processo='NPF3001',
            data_nascimento=datetime.date(2010, 1, 1), sexo='M',
            turma=self.turma, encarregado=encarregado,
        )

        self.falta = Frequencia.objects.create(
            aluno=self.aluno, atribuicao=self.atribuicao,
            data=datetime.date(2026, 3, 1), estado=Frequencia.FALTA,
        )
        self.justificacao = JustificacaoFalta.objects.create(
            frequencia=self.falta, motivo='Consulta médica'
        )


class PermissaoValidarJustificacaoTests(JustificacaoFase3TestBase):
    def test_professor_da_disciplina_sem_ser_diretor_de_turma_nao_aprova(self):
        # Tightening da Fase 3: antes, qualquer professor da disciplina
        # podia aprovar; agora só o Sub-diretor ou o Diretor de Turma.
        self.client.login(username='prof_f3', password='senha123')
        response = self.client.post(reverse('justificacao_aprovar', args=[self.justificacao.pk]))

        self.assertEqual(response.status_code, 403)
        self.justificacao.refresh_from_db()
        self.assertFalse(self.justificacao.aprovada)

    def test_diretor_de_turma_aprova(self):
        self.client.login(username='dt_f3', password='senha123')
        response = self.client.post(reverse('justificacao_aprovar', args=[self.justificacao.pk]))

        self.assertRedirects(response, reverse('justificacao_lista'))
        self.justificacao.refresh_from_db()
        self.assertTrue(self.justificacao.aprovada)

    def test_subdiretor_aprova(self):
        self.client.login(username='subdir_f3', password='senha123')
        response = self.client.post(reverse('justificacao_aprovar', args=[self.justificacao.pk]))

        self.assertRedirects(response, reverse('justificacao_lista'))
        self.justificacao.refresh_from_db()
        self.assertTrue(self.justificacao.aprovada)


class AnaliseCoordenadorTurnoTests(JustificacaoFase3TestBase):
    def test_coordenador_do_turno_analisa_e_notifica_diretor_de_turma(self):
        self.client.login(username='coord_turno_f3', password='senha123')
        response = self.client.post(
            reverse('justificacao_analisar', args=[self.justificacao.pk]),
            {'parecer_coordenador': 'Aluno com 3 faltas este mês, motivo plausível.'},
        )

        self.assertRedirects(response, reverse('justificacao_lista'))
        self.justificacao.refresh_from_db()
        self.assertEqual(
            self.justificacao.parecer_coordenador,
            'Aluno com 3 faltas este mês, motivo plausível.',
        )
        self.assertEqual(self.justificacao.coordenador_turno, self.coordenador_turno)
        self.assertIsNotNone(self.justificacao.analisada_em)

        notificacao = Notificacao.objects.get(destinatario__username='dt_f3')
        self.assertIn('parecer', notificacao.titulo.lower())

    def test_coordenador_de_outro_turno_nao_pode_analisar(self):
        self.client.login(username='coord_turno_manha_f3', password='senha123')
        response = self.client.post(
            reverse('justificacao_analisar', args=[self.justificacao.pk]),
            {'parecer_coordenador': 'Tentativa fora do âmbito.'},
        )

        self.assertEqual(response.status_code, 403)
        self.justificacao.refresh_from_db()
        self.assertEqual(self.justificacao.parecer_coordenador, '')

    def test_coordenador_turno_nao_pode_aprovar_diretamente(self):
        self.client.login(username='coord_turno_f3', password='senha123')
        response = self.client.post(reverse('justificacao_aprovar', args=[self.justificacao.pk]))

        self.assertEqual(response.status_code, 403)


class ListaJustificacoesEscopoTests(JustificacaoFase3TestBase):
    def test_coordenador_turno_ve_so_justificacoes_do_seu_turno(self):
        self.client.login(username='coord_turno_f3', password='senha123')
        response = self.client.get(reverse('justificacao_lista'))

        self.assertEqual(response.status_code, 200)
        ids = {j.pk for j in response.context['justificacoes']}
        self.assertEqual(ids, {self.justificacao.pk})

    def test_coordenador_de_outro_turno_nao_ve_justificacao(self):
        self.client.login(username='coord_turno_manha_f3', password='senha123')
        response = self.client.get(reverse('justificacao_lista'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['justificacoes']), 0)
