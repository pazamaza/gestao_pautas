import datetime

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from alunos.models import Aluno, Encarregado
from disciplinas.models import Disciplina
from notificacoes.models import Notificacao
from professores.models import AtribuicaoDocente, DiretorTurma, Professor
from turmas.models import AnoLetivo, Classe, PeriodoAcademico, Turma

from .models import Avaliacao, Nota


class PautasTestBase(TestCase):
    def setUp(self):
        self.grupo_admin = Group.objects.create(name='Administrador')
        self.grupo_professor = Group.objects.create(name='Professor')

        self.admin_user = User.objects.create_user(username='admin', password='senha123')
        self.admin_user.groups.add(self.grupo_admin)

        self.professor_user = User.objects.create_user(username='prof', password='senha123')
        self.professor_user.groups.add(self.grupo_professor)
        self.professor = Professor.objects.create(
            user=self.professor_user, numero_funcionario='P001'
        )

        self.outro_professor_user = User.objects.create_user(username='outro_prof', password='senha123')
        self.outro_professor_user.groups.add(self.grupo_professor)
        self.outro_professor = Professor.objects.create(
            user=self.outro_professor_user, numero_funcionario='P002'
        )

        self.ano_letivo = AnoLetivo.objects.create(descricao='2026')
        self.classe = Classe.objects.create(nome='7ª Classe')
        self.turma = Turma.objects.create(nome='A', classe=self.classe, ano_letivo=self.ano_letivo)
        self.disciplina = Disciplina.objects.create(nome='Matemática', sigla='MAT')

        self.periodo = PeriodoAcademico.objects.create(
            nome='1º Trimestre', ano_letivo=self.ano_letivo, aberto=True
        )

        self.atribuicao = AtribuicaoDocente.objects.create(
            professor=self.professor,
            disciplina=self.disciplina,
            turma=self.turma,
            ano_letivo=self.ano_letivo,
        )

        self.avaliacao = Avaliacao.objects.create(
            atribuicao=self.atribuicao, periodo=self.periodo
        )

        encarregado_user = User.objects.create_user(username='encarregado1', password='senha123')
        self.encarregado = Encarregado.objects.create(user=encarregado_user, telefone='900000000')
        self.aluno = Aluno.objects.create(
            nome='Aluno Teste',
            numero_processo='NP001',
            data_nascimento=datetime.date(2010, 1, 1),
            sexo='M',
            turma=self.turma,
            encarregado=self.encarregado,
        )

        self.nota = Nota.objects.create(
            avaliacao=self.avaliacao, aluno=self.aluno, mac=10, npp=10, npt=10
        )


class PeriodoLancamentoTests(PautasTestBase):
    def test_nota_form_bloqueia_fora_do_periodo(self):
        self.periodo.aberto = False
        self.periodo.save()

        self.client.login(username='prof', password='senha123')
        response = self.client.post(
            reverse('nota_editar', args=[self.nota.pk]),
            {
                'avaliacao': self.avaliacao.pk,
                'aluno': self.aluno.pk,
                'mac': 15,
                'npp': 15,
                'npt': 15,
                'observacao': '',
            },
        )

        self.nota.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.nota.mac, 10)

    def test_nota_form_permite_dentro_do_periodo(self):
        self.client.login(username='prof', password='senha123')
        response = self.client.post(
            reverse('nota_editar', args=[self.nota.pk]),
            {
                'avaliacao': self.avaliacao.pk,
                'aluno': self.aluno.pk,
                'mac': 15,
                'npp': 15,
                'npt': 15,
                'observacao': '',
            },
        )

        self.nota.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.nota.mac, 15)


class ValidacaoAvaliacaoTests(PautasTestBase):
    def test_admin_valida_avaliacao(self):
        self.client.login(username='admin', password='senha123')
        response = self.client.get(reverse('avaliacao_validar', args=[self.avaliacao.pk]))

        self.avaliacao.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.avaliacao.status, Avaliacao.STATUS_VALIDADA)
        self.assertEqual(self.avaliacao.validado_por, self.admin_user)

    def test_admin_reporta_erro_notifica_professor_e_diretor(self):
        DiretorTurma.objects.create(
            professor=self.outro_professor, turma=self.turma, ano_letivo=self.ano_letivo
        )

        self.client.login(username='admin', password='senha123')
        response = self.client.post(
            reverse('avaliacao_reportar_erro', args=[self.avaliacao.pk]),
            {'observacoes_validacao': 'Nota do aluno X está incorreta.'},
        )

        self.avaliacao.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.avaliacao.status, Avaliacao.STATUS_COM_ERROS)

        destinatarios = set(
            Notificacao.objects.values_list('destinatario__username', flat=True)
        )
        self.assertIn('prof', destinatarios)
        self.assertIn('outro_prof', destinatarios)

    def test_professor_nao_acede_a_validar(self):
        self.client.login(username='prof', password='senha123')
        response = self.client.get(reverse('avaliacao_validar', args=[self.avaliacao.pk]))
        self.assertEqual(response.status_code, 403)


class PermissoesPautasTests(PautasTestBase):
    def test_admin_nao_acede_a_criar_nota(self):
        self.client.login(username='admin', password='senha123')
        response = self.client.get(reverse('nota_nova'))
        self.assertEqual(response.status_code, 403)

    def test_professor_acede_a_criar_nota(self):
        self.client.login(username='prof', password='senha123')
        response = self.client.get(reverse('nota_nova'))
        self.assertEqual(response.status_code, 200)

    def test_resultado_disciplina_edicao_requer_superuser(self):
        self.client.login(username='admin', password='senha123')
        response = self.client.get(reverse('resultado_novo'))
        self.assertEqual(response.status_code, 403)

        self.admin_user.is_superuser = True
        self.admin_user.save()
        response = self.client.get(reverse('resultado_novo'))
        self.assertEqual(response.status_code, 200)

    def test_anonimo_redirecionado_para_login(self):
        response = self.client.get(reverse('avaliacao_lista'))
        self.assertEqual(response.status_code, 302)
