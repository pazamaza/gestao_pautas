from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from turmas.models import AnoLetivo, Classe, Turma
from .models import Aluno, Encarregado


class CadastroCrudTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Sub-diretor Pedagógico')
        self.admin = User.objects.create_user(username='admin', password='senha123')
        self.admin.groups.add(Group.objects.get(name='Sub-diretor Pedagógico'))
        self.client.login(username='admin', password='senha123')

        ano_letivo = AnoLetivo.objects.create(descricao='2026')
        classe = Classe.objects.create(nome='10ª Classe')
        self.turma = Turma.objects.create(nome='A', classe=classe, ano_letivo=ano_letivo)

        encarregado_user = User.objects.create_user(username='encarregado1', password='x')
        self.encarregado = Encarregado.objects.create(user=encarregado_user, telefone='900000000')

        self.aluno = Aluno.objects.create(
            nome='Aluno Teste',
            numero_processo='P1',
            data_nascimento='2010-01-01',
            sexo='M',
            turma=self.turma,
            encarregado=self.encarregado,
        )

    def test_criar_aluno_redireciona_para_lista(self):
        response = self.client.post(reverse('aluno_novo'), {
            'nome': 'Novo Aluno',
            'numero_processo': 'P2',
            'data_nascimento': '2011-02-02',
            'sexo': 'F',
            'turma': self.turma.pk,
            'encarregado': self.encarregado.pk,
            'estado': Aluno.ESTADO_ATIVO,
        })

        self.assertRedirects(response, reverse('aluno_lista'))
        self.assertTrue(Aluno.objects.filter(numero_processo='P2').exists())

    def test_lista_alunos_mostra_acoes(self):
        response = self.client.get(reverse('aluno_lista'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('aluno_novo'))
        self.assertContains(response, reverse('aluno_editar', args=[self.aluno.pk]))
        self.assertContains(response, reverse('aluno_excluir', args=[self.aluno.pk]))

    def test_lista_encarregados_mostra_acoes(self):
        response = self.client.get(reverse('encarregado_lista'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('encarregado_detalhe', args=[self.encarregado.pk]))
        self.assertContains(response, reverse('encarregado_editar', args=[self.encarregado.pk]))
        self.assertContains(response, reverse('encarregado_excluir', args=[self.encarregado.pk]))

    def test_visualizar_e_editar_encarregado(self):
        response = self.client.get(reverse('encarregado_detalhe', args=[self.encarregado.pk]))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('encarregado_editar', args=[self.encarregado.pk]), {
            'first_name': 'Editado',
            'email': 'editado@example.com',
            'telefone': '911111111',
        })
        self.assertRedirects(response, reverse('encarregado_lista'))
        self.encarregado.refresh_from_db()
        self.assertEqual(self.encarregado.telefone, '911111111')

    def test_eliminar_encarregado_com_aluno_associado_mostra_erro(self):
        response = self.client.post(reverse('encarregado_excluir', args=[self.encarregado.pk]))

        self.assertRedirects(response, reverse('encarregado_lista'))
        self.assertTrue(Encarregado.objects.filter(pk=self.encarregado.pk).exists())

    def test_eliminar_encarregado_sem_dependentes(self):
        outro_user = User.objects.create_user(username='encarregado2', password='x')
        outro = Encarregado.objects.create(user=outro_user, telefone='900000001')

        response = self.client.post(reverse('encarregado_excluir', args=[outro.pk]))

        self.assertRedirects(response, reverse('encarregado_lista'))
        self.assertFalse(Encarregado.objects.filter(pk=outro.pk).exists())
