from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .models import AnoLetivo, Classe, PeriodoAcademico, Turma


class CadastroCrudTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Administrador')
        self.admin = User.objects.create_user(username='admin', password='senha123')
        self.admin.groups.add(Group.objects.get(name='Administrador'))
        self.client.login(username='admin', password='senha123')

        self.ano_letivo = AnoLetivo.objects.create(descricao='2026')
        classe = Classe.objects.create(nome='10ª Classe')
        self.turma = Turma.objects.create(nome='A', classe=classe, ano_letivo=self.ano_letivo)
        self.periodo = PeriodoAcademico.objects.create(nome='1º Trimestre', ano_letivo=self.ano_letivo)

    def test_lista_turmas_mostra_acoes(self):
        response = self.client.get(reverse('turma_lista'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('turma_novo'))
        self.assertContains(response, reverse('turma_detalhe', args=[self.turma.pk]))
        self.assertContains(response, reverse('turma_editar', args=[self.turma.pk]))
        self.assertContains(response, reverse('turma_desativar', args=[self.turma.pk]))

    def test_detalhe_e_desativar_reativar_turma(self):
        response = self.client.get(reverse('turma_detalhe', args=[self.turma.pk]))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('turma_desativar', args=[self.turma.pk]))
        self.assertRedirects(response, reverse('turma_lista'))
        self.turma.refresh_from_db()
        self.assertFalse(self.turma.ativo)

        response = self.client.get(reverse('turma_reativar', args=[self.turma.pk]))
        self.assertRedirects(response, reverse('turma_lista'))
        self.turma.refresh_from_db()
        self.assertTrue(self.turma.ativo)

    def test_lista_periodos_mostra_acoes(self):
        response = self.client.get(reverse('periodo_lista'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('periodo_detalhe', args=[self.periodo.pk]))
        self.assertContains(response, reverse('periodo_editar', args=[self.periodo.pk]))

    def test_detalhe_periodo(self):
        response = self.client.get(reverse('periodo_detalhe', args=[self.periodo.pk]))
        self.assertEqual(response.status_code, 200)
