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
        self.grupo_admin, _ = Group.objects.get_or_create(name='Administrador')
        self.grupo_professor, _ = Group.objects.get_or_create(name='Professor')

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
        self.classe, _ = Classe.objects.get_or_create(nome='7ª Classe')
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
            avaliacao=self.avaliacao, aluno=self.aluno, mac=10, npt=10
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


class DiretorTurmaVisualizaPautaTests(PautasTestBase):
    def setUp(self):
        super().setUp()
        DiretorTurma.objects.create(
            professor=self.outro_professor, turma=self.turma, ano_letivo=self.ano_letivo
        )

    def test_diretor_de_turma_ve_pauta_de_outra_disciplina(self):
        self.client.login(username='outro_prof', password='senha123')
        response = self.client.get(reverse('pauta_trimestral', args=[self.avaliacao.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Importar Notas')
        self.assertContains(response, 'diretor de turma')

    def test_diretor_de_turma_nao_pode_importar_notas(self):
        self.client.login(username='outro_prof', password='senha123')
        response = self.client.post(
            reverse('pauta_importar_excel', args=[self.avaliacao.pk]), {}
        )
        self.assertEqual(response.status_code, 403)

    def test_professor_sem_relacao_com_a_turma_nao_ve_pauta(self):
        terceiro_user = User.objects.create_user(username='terceiro_prof', password='senha123')
        terceiro_user.groups.add(self.grupo_professor)
        Professor.objects.create(user=terceiro_user, numero_funcionario='P003')

        self.client.login(username='terceiro_prof', password='senha123')
        response = self.client.get(reverse('pauta_trimestral', args=[self.avaliacao.pk]))
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


class ConsultaPautasTests(PautasTestBase):
    def setUp(self):
        super().setUp()

        grupo_aluno, _ = Group.objects.get_or_create(name='Aluno')
        grupo_encarregado, _ = Group.objects.get_or_create(name='Encarregado')

        self.aluno_user = User.objects.create_user(username='aluno1', password='senha123')
        self.aluno_user.groups.add(grupo_aluno)
        self.aluno.user = self.aluno_user
        self.aluno.save()

        self.encarregado_user = self.encarregado.user
        self.encarregado_user.groups.add(grupo_encarregado)

        self.avaliacao.status = Avaliacao.STATUS_VALIDADA
        self.avaliacao.save()

        outro_periodo = PeriodoAcademico.objects.create(
            nome='2º Trimestre', ano_letivo=self.ano_letivo, aberto=True
        )
        self.avaliacao_com_erros = Avaliacao.objects.create(
            atribuicao=self.atribuicao, periodo=outro_periodo, status=Avaliacao.STATUS_COM_ERROS
        )
        Nota.objects.create(
            avaliacao=self.avaliacao_com_erros, aluno=self.aluno, mac=5, npt=5
        )

        outro_encarregado_user = User.objects.create_user(username='encarregado2', password='senha123')
        outro_encarregado_user.groups.add(grupo_encarregado)
        self.outro_encarregado = Encarregado.objects.create(
            user=outro_encarregado_user, telefone='911111111'
        )
        self.outro_aluno = Aluno.objects.create(
            nome='Outro Aluno',
            numero_processo='NP002',
            data_nascimento=datetime.date(2011, 2, 2),
            sexo='F',
            turma=self.turma,
            encarregado=self.outro_encarregado,
        )

    def test_aluno_ve_apenas_notas_validadas(self):
        self.client.login(username='aluno1', password='senha123')
        response = self.client.get(reverse('minhas_notas'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1º Trimestre')
        self.assertNotContains(response, '2º Trimestre')

    def test_aluno_sem_registo_associado_ve_mensagem_amigavel(self):
        sem_registo = User.objects.create_user(username='sem_registo', password='senha123')
        sem_registo.groups.add(Group.objects.get(name='Aluno'))

        self.client.login(username='sem_registo', password='senha123')
        response = self.client.get(reverse('minhas_notas'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'não está associada a um registo de aluno')

    def test_encarregado_ve_notas_validadas_do_dependente(self):
        self.client.login(username='encarregado1', password='senha123')
        response = self.client.get(reverse('notas_dependente', args=[self.aluno.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1º Trimestre')
        self.assertNotContains(response, '2º Trimestre')

    def test_encarregado_nao_acede_a_dependente_de_outro(self):
        self.client.login(username='encarregado1', password='senha123')
        response = self.client.get(reverse('notas_dependente', args=[self.outro_aluno.id]))

        self.assertEqual(response.status_code, 403)

    def test_encarregado_lista_dependentes(self):
        self.client.login(username='encarregado1', password='senha123')
        response = self.client.get(reverse('meus_dependentes'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Aluno Teste')
        self.assertNotContains(response, 'Outro Aluno')
