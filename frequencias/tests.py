import datetime

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from alunos.models import Aluno, Encarregado
from disciplinas.models import Disciplina
from professores.models import AtribuicaoDocente, Professor
from turmas.models import AnoLetivo, Classe, Turma

from .models import Frequencia, JustificacaoFalta


class FrequenciaTestBase(TestCase):
    def setUp(self):
        self.grupo_admin, _ = Group.objects.get_or_create(name='Administrador')
        self.grupo_professor, _ = Group.objects.get_or_create(name='Professor')
        self.grupo_aluno, _ = Group.objects.get_or_create(name='Aluno')
        self.grupo_encarregado, _ = Group.objects.get_or_create(name='Encarregado')

        self.admin_user = User.objects.create_user(username='admin', password='senha123')
        self.admin_user.groups.add(self.grupo_admin)

        self.professor_user = User.objects.create_user(username='prof', password='senha123')
        self.professor_user.groups.add(self.grupo_professor)
        self.professor = Professor.objects.create(user=self.professor_user, numero_funcionario='P001')

        self.outro_professor_user = User.objects.create_user(username='outro_prof', password='senha123')
        self.outro_professor_user.groups.add(self.grupo_professor)
        self.outro_professor = Professor.objects.create(
            user=self.outro_professor_user, numero_funcionario='P002'
        )

        self.ano_letivo = AnoLetivo.objects.create(descricao='2026')
        self.classe, _ = Classe.objects.get_or_create(nome='7ª Classe')
        self.turma = Turma.objects.create(nome='A', classe=self.classe, ano_letivo=self.ano_letivo)
        self.disciplina = Disciplina.objects.create(nome='Matemática', sigla='MAT')

        self.atribuicao = AtribuicaoDocente.objects.create(
            professor=self.professor,
            disciplina=self.disciplina,
            turma=self.turma,
            ano_letivo=self.ano_letivo,
        )
        self.outra_atribuicao = AtribuicaoDocente.objects.create(
            professor=self.outro_professor,
            disciplina=self.disciplina,
            turma=self.turma,
            ano_letivo=self.ano_letivo,
        )

        encarregado_user = User.objects.create_user(username='encarregado1', password='senha123')
        encarregado_user.groups.add(self.grupo_encarregado)
        self.encarregado = Encarregado.objects.create(user=encarregado_user, telefone='900000000')

        outro_encarregado_user = User.objects.create_user(username='encarregado2', password='senha123')
        outro_encarregado_user.groups.add(self.grupo_encarregado)
        self.outro_encarregado = Encarregado.objects.create(
            user=outro_encarregado_user, telefone='911111111'
        )

        self.aluno_user = User.objects.create_user(username='aluno1', password='senha123')
        self.aluno_user.groups.add(self.grupo_aluno)
        self.aluno = Aluno.objects.create(
            user=self.aluno_user,
            nome='Aluno Teste',
            numero_processo='NP001',
            data_nascimento=datetime.date(2010, 1, 1),
            sexo='M',
            turma=self.turma,
            encarregado=self.encarregado,
        )

        self.outro_aluno = Aluno.objects.create(
            nome='Outro Aluno',
            numero_processo='NP002',
            data_nascimento=datetime.date(2011, 2, 2),
            sexo='F',
            turma=self.turma,
            encarregado=self.outro_encarregado,
        )

        self.frequencia_aluno = Frequencia.objects.create(
            aluno=self.aluno, atribuicao=self.atribuicao,
            data=datetime.date(2026, 3, 1), estado='P',
        )
        self.frequencia_outro_aluno = Frequencia.objects.create(
            aluno=self.outro_aluno, atribuicao=self.outra_atribuicao,
            data=datetime.date(2026, 3, 2), estado='F',
        )


class FrequenciaListagemTests(FrequenciaTestBase):
    def test_anonimo_redirecionado_para_login(self):
        response = self.client.get(reverse('frequencia_lista'))
        self.assertEqual(response.status_code, 302)

    def test_admin_ve_todas_as_frequencias(self):
        self.client.login(username='admin', password='senha123')
        response = self.client.get(reverse('frequencia_lista'))
        self.assertContains(response, 'Aluno Teste')
        self.assertContains(response, 'Outro Aluno')

    def test_professor_ve_apenas_as_suas_atribuicoes(self):
        self.client.login(username='prof', password='senha123')
        response = self.client.get(reverse('frequencia_lista'))
        self.assertContains(response, 'Aluno Teste')
        self.assertNotContains(response, 'Outro Aluno')

    def test_aluno_ve_apenas_as_suas_proprias_frequencias(self):
        self.client.login(username='aluno1', password='senha123')
        response = self.client.get(reverse('frequencia_lista'))
        self.assertContains(response, 'Aluno Teste')
        self.assertNotContains(response, 'Outro Aluno')

    def test_encarregado_ve_apenas_frequencias_do_dependente(self):
        self.client.login(username='encarregado1', password='senha123')
        response = self.client.get(reverse('frequencia_lista'))
        self.assertContains(response, 'Aluno Teste')
        self.assertNotContains(response, 'Outro Aluno')


class FrequenciaGestaoTests(FrequenciaTestBase):
    def test_aluno_nao_acede_a_criar_frequencia(self):
        self.client.login(username='aluno1', password='senha123')
        response = self.client.get(reverse('frequencia_form'))
        self.assertEqual(response.status_code, 403)

    def test_encarregado_nao_acede_a_criar_frequencia(self):
        self.client.login(username='encarregado1', password='senha123')
        response = self.client.get(reverse('frequencia_form'))
        self.assertEqual(response.status_code, 403)

    def test_professor_acede_a_criar_frequencia(self):
        self.client.login(username='prof', password='senha123')
        response = self.client.get(reverse('frequencia_form'))
        self.assertEqual(response.status_code, 200)

    def test_professor_nao_edita_frequencia_de_outra_atribuicao(self):
        self.client.login(username='prof', password='senha123')
        response = self.client.get(
            reverse('frequencia_editar', args=[self.frequencia_outro_aluno.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_professor_edita_frequencia_da_sua_atribuicao(self):
        self.client.login(username='prof', password='senha123')
        response = self.client.get(
            reverse('frequencia_editar', args=[self.frequencia_aluno.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_admin_edita_frequencia_de_qualquer_atribuicao(self):
        self.client.login(username='admin', password='senha123')
        response = self.client.get(
            reverse('frequencia_editar', args=[self.frequencia_outro_aluno.pk])
        )
        self.assertEqual(response.status_code, 200)


class JustificacaoFaltaTests(FrequenciaTestBase):
    def setUp(self):
        super().setUp()
        self.falta_aluno = Frequencia.objects.create(
            aluno=self.aluno, atribuicao=self.atribuicao,
            data=datetime.date(2026, 7, 14), estado='F',
        )

    def test_aluno_consegue_submeter_justificacao_da_sua_falta(self):
        self.client.login(username='aluno1', password='senha123')
        response = self.client.post(
            reverse('justificacao_criar', args=[self.falta_aluno.pk]),
            {'motivo': 'Consulta médica'},
        )
        self.assertRedirects(response, reverse('frequencia_lista'))
        justificacao = JustificacaoFalta.objects.get(frequencia=self.falta_aluno)
        self.assertEqual(justificacao.motivo, 'Consulta médica')
        self.assertFalse(justificacao.aprovada)

    def test_encarregado_consegue_submeter_justificacao_do_dependente(self):
        self.client.login(username='encarregado1', password='senha123')
        response = self.client.post(
            reverse('justificacao_criar', args=[self.falta_aluno.pk]),
            {'motivo': 'Doença'},
        )
        self.assertRedirects(response, reverse('frequencia_lista'))
        self.assertTrue(JustificacaoFalta.objects.filter(frequencia=self.falta_aluno).exists())

    def test_aluno_nao_justifica_falta_de_outro_aluno(self):
        self.client.login(username='aluno1', password='senha123')
        response = self.client.get(
            reverse('justificacao_criar', args=[self.frequencia_outro_aluno.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_encarregado_nao_justifica_falta_de_dependente_alheio(self):
        self.client.login(username='encarregado1', password='senha123')
        response = self.client.get(
            reverse('justificacao_criar', args=[self.frequencia_outro_aluno.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_professor_nao_acede_a_justificar_falta(self):
        self.client.login(username='prof', password='senha123')
        response = self.client.get(
            reverse('justificacao_criar', args=[self.falta_aluno.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_nao_pode_justificar_registo_que_nao_e_falta(self):
        self.client.login(username='aluno1', password='senha123')
        response = self.client.get(
            reverse('justificacao_criar', args=[self.frequencia_aluno.pk])
        )
        self.assertRedirects(response, reverse('frequencia_lista'))
        self.assertFalse(JustificacaoFalta.objects.filter(frequencia=self.frequencia_aluno).exists())

    def test_justificacao_aprovada_nao_pode_ser_reeditada(self):
        justificacao = JustificacaoFalta.objects.create(
            frequencia=self.falta_aluno, motivo='Motivo inicial', aprovada=True,
        )
        self.client.login(username='aluno1', password='senha123')
        response = self.client.post(
            reverse('justificacao_criar', args=[self.falta_aluno.pk]),
            {'motivo': 'Tentativa de alterar'},
        )
        self.assertRedirects(response, reverse('frequencia_lista'))
        justificacao.refresh_from_db()
        self.assertEqual(justificacao.motivo, 'Motivo inicial')
