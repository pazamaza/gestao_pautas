from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from disciplinas.models import Disciplina
from turmas.models import AnoLetivo, Classe, Turma
from .models import AtribuicaoDocente, DiretorTurma, Professor


class CadastroCrudTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Administrador')
        Group.objects.get_or_create(name='Professor')
        self.admin = User.objects.create_user(username='admin', password='senha123')
        self.admin.groups.add(Group.objects.get(name='Administrador'))
        self.client.login(username='admin', password='senha123')

        prof_user = User.objects.create_user(username='prof1', password='x')
        prof_user.groups.add(Group.objects.get(name='Professor'))
        self.professor = Professor.objects.create(user=prof_user, numero_funcionario='F1')

        self.ano_letivo = AnoLetivo.objects.create(descricao='2026')
        classe = Classe.objects.create(nome='10ª Classe')
        self.turma = Turma.objects.create(nome='A', classe=classe, ano_letivo=self.ano_letivo)
        self.disciplina = Disciplina.objects.create(nome='Matemática', sigla='MAT')

        self.atribuicao = AtribuicaoDocente.objects.create(
            professor=self.professor, disciplina=self.disciplina,
            turma=self.turma, ano_letivo=self.ano_letivo,
        )
        self.diretor = DiretorTurma.objects.create(
            professor=self.professor, turma=self.turma, ano_letivo=self.ano_letivo,
        )

    def test_lista_professores_mostra_acoes(self):
        response = self.client.get(reverse('professor_lista'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('professor_novo'))
        self.assertContains(response, reverse('professor_detalhe', args=[self.professor.pk]))
        self.assertContains(response, reverse('professor_editar', args=[self.professor.pk]))
        self.assertContains(response, reverse('professor_excluir', args=[self.professor.pk]))

    def test_lista_professores_agrupa_por_disciplina_sem_repetir_nome(self):
        outra_disciplina = Disciplina.objects.create(nome='Física', sigla='FIS')
        outra_classe = Classe.objects.create(nome='Iº Ano')
        outra_turma = Turma.objects.create(nome='B', classe=outra_classe, ano_letivo=self.ano_letivo)
        AtribuicaoDocente.objects.create(
            professor=self.professor, disciplina=outra_disciplina,
            turma=outra_turma, ano_letivo=self.ano_letivo,
        )

        response = self.client.get(reverse('professor_lista'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Matemática')
        self.assertContains(response, 'Física')
        self.assertContains(response, str(self.professor), count=1)
        self.assertContains(response, 'rowspan="2"', count=6)

    def test_detalhe_professor(self):
        response = self.client.get(reverse('professor_detalhe', args=[self.professor.pk]))
        self.assertEqual(response.status_code, 200)

    def test_form_nova_atribuicao_vem_com_ativo_marcado_por_omissao(self):
        response = self.client.get(reverse('atribuicao_nova'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].initial.get('ativo'))

    def test_form_novo_diretor_turma_vem_com_ativo_marcado_por_omissao(self):
        response = self.client.get(reverse('diretor_turma_novo'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].initial.get('ativo'))

    def test_criar_atribuicao_sem_tocar_no_checkbox_fica_ativa(self):
        outra_turma = Turma.objects.create(
            nome='C', classe=self.turma.classe, ano_letivo=self.ano_letivo
        )
        response = self.client.post(reverse('atribuicao_nova'), {
            'professor': self.professor.pk,
            'disciplina': self.disciplina.pk,
            'turma': outra_turma.pk,
            'ano_letivo': self.ano_letivo.pk,
            'ativo': 'on',
        })
        self.assertRedirects(response, reverse('atribuicao_lista'))
        nova = AtribuicaoDocente.objects.get(turma=outra_turma)
        self.assertTrue(nova.ativo)

    def test_lista_atribuicoes_mostra_matriz_com_link_para_detalhe(self):
        response = self.client.get(reverse('atribuicao_lista'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('atribuicao_nova'))
        self.assertContains(response, reverse('atribuicao_detalhe', args=[self.atribuicao.pk]))
        self.assertContains(response, 'bg-success')
        self.assertContains(response, self.turma.nome)
        self.assertContains(response, str(self.turma.classe))

    def test_detalhe_atribuicao(self):
        response = self.client.get(reverse('atribuicao_detalhe', args=[self.atribuicao.pk]))
        self.assertEqual(response.status_code, 200)

    def test_lista_atribuicoes_agrupa_por_professor_sem_repetir_nome(self):
        outra_disciplina = Disciplina.objects.create(nome='Física', sigla='FIS')
        AtribuicaoDocente.objects.create(
            professor=self.professor, disciplina=outra_disciplina,
            turma=self.turma, ano_letivo=self.ano_letivo,
        )

        response = self.client.get(reverse('atribuicao_lista'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Matemática')
        self.assertContains(response, 'Física')
        self.assertContains(response, str(self.professor), count=1)
        self.assertContains(response, '<td rowspan="2"', count=1)

    def test_matriz_mostra_badge_cinza_para_atribuicao_inativa(self):
        self.atribuicao.ativo = False
        self.atribuicao.save()

        response = self.client.get(reverse('atribuicao_lista'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'bg-secondary')

    def test_detalhe_atribuicao_mostra_botao_desativar_ou_reativar(self):
        response = self.client.get(reverse('atribuicao_detalhe', args=[self.atribuicao.pk]))
        self.assertContains(response, reverse('atribuicao_desativar', args=[self.atribuicao.pk]))

        self.atribuicao.ativo = False
        self.atribuicao.save()
        response = self.client.get(reverse('atribuicao_detalhe', args=[self.atribuicao.pk]))
        self.assertContains(response, reverse('atribuicao_reativar', args=[self.atribuicao.pk]))

    def test_editar_atribuicao(self):
        response = self.client.get(reverse('atribuicao_editar', args=[self.atribuicao.pk]))
        self.assertEqual(response.status_code, 200)

    def test_desativar_e_reativar_atribuicao(self):
        response = self.client.get(reverse('atribuicao_desativar', args=[self.atribuicao.pk]))
        self.assertRedirects(response, reverse('atribuicao_lista'))
        self.atribuicao.refresh_from_db()
        self.assertFalse(self.atribuicao.ativo)

        response = self.client.get(reverse('atribuicao_reativar', args=[self.atribuicao.pk]))
        self.assertRedirects(response, reverse('atribuicao_lista'))
        self.atribuicao.refresh_from_db()
        self.assertTrue(self.atribuicao.ativo)

    def test_lista_diretores_turma_mostra_acoes(self):
        response = self.client.get(reverse('diretor_turma_lista'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('diretor_turma_detalhe', args=[self.diretor.pk]))
        self.assertContains(response, reverse('diretor_turma_excluir', args=[self.diretor.pk]))

    def test_detalhe_e_eliminar_diretor_turma(self):
        response = self.client.get(reverse('diretor_turma_detalhe', args=[self.diretor.pk]))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('diretor_turma_excluir', args=[self.diretor.pk]))
        self.assertRedirects(response, reverse('diretor_turma_lista'))
        self.assertFalse(DiretorTurma.objects.filter(pk=self.diretor.pk).exists())
