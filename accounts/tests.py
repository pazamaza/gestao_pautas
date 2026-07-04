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
