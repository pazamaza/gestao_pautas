from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .utils import eh_administrador, eh_professor


class PapeisUsuarioTests(TestCase):
    def setUp(self):
        Group.objects.create(name='Administrador')
        Group.objects.create(name='Professor')

    def test_superuser_eh_administrador_sem_grupo(self):
        user = User.objects.create_user(username='super', password='x', is_superuser=True)
        self.assertTrue(eh_administrador(user))

    def test_usuario_no_grupo_administrador_eh_administrador(self):
        user = User.objects.create_user(username='adm', password='x')
        user.groups.add(Group.objects.get(name='Administrador'))
        self.assertTrue(eh_administrador(user))

    def test_usuario_sem_grupo_nao_eh_administrador_nem_professor(self):
        user = User.objects.create_user(username='comum', password='x')
        self.assertFalse(eh_administrador(user))
        self.assertFalse(eh_professor(user))


class DashboardViewTests(TestCase):
    def setUp(self):
        Group.objects.create(name='Administrador')

    def test_dashboard_admin_renderiza_template_admin(self):
        user = User.objects.create_user(username='adm', password='senha123')
        user.groups.add(Group.objects.get(name='Administrador'))
        self.client.login(username='adm', password='senha123')

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboards/admin.html')

    def test_dashboard_sem_grupo_mostra_sem_permissao(self):
        User.objects.create_user(username='ninguem', password='senha123')
        self.client.login(username='ninguem', password='senha123')

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboards/sem_permissao.html')


class DashboardPapelEspecificoTests(TestCase):
    def setUp(self):
        Group.objects.create(name='Professor')
        Group.objects.create(name='Aluno')
        Group.objects.create(name='Encarregado')

    def test_dashboard_professor(self):
        from professores.models import Professor

        user = User.objects.create_user(username='prof', password='senha123')
        user.groups.add(Group.objects.get(name='Professor'))
        Professor.objects.create(user=user, numero_funcionario='P100')

        self.client.login(username='prof', password='senha123')
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboards/professor.html')

    def test_dashboard_aluno_sem_registo_associado(self):
        user = User.objects.create_user(username='aluno1', password='senha123')
        user.groups.add(Group.objects.get(name='Aluno'))

        self.client.login(username='aluno1', password='senha123')
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboards/aluno.html')
        self.assertContains(response, 'não está associada a um registo de aluno')

    def test_dashboard_encarregado_sem_dependentes(self):
        user = User.objects.create_user(username='enc1', password='senha123')
        user.groups.add(Group.objects.get(name='Encarregado'))

        self.client.login(username='enc1', password='senha123')
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboards/encarregado.html')
