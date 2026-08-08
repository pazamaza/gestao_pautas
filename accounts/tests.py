from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .utils import eh_administrador, eh_professor


class PapeisUsuarioTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Administrador')
        Group.objects.get_or_create(name='Professor')

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
        Group.objects.get_or_create(name='Administrador')

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
        Group.objects.get_or_create(name='Professor')
        Group.objects.get_or_create(name='Aluno')
        Group.objects.get_or_create(name='Encarregado')

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


class AdministradorCrudTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Administrador')
        self.superuser = User.objects.create_superuser(
            username='root', password='senha123', email='root@example.com'
        )
        self.client.login(username='root', password='senha123')

    def test_administrador_do_grupo_sem_superuser_nao_acede(self):
        user = User.objects.create_user(username='adm_comum', password='senha123')
        user.groups.add(Group.objects.get(name='Administrador'))
        self.client.logout()
        self.client.login(username='adm_comum', password='senha123')

        response = self.client.get(reverse('administrador_lista'))

        self.assertEqual(response.status_code, 403)

    def test_lista_administradores_inclui_superuser(self):
        response = self.client.get(reverse('administrador_lista'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'root')

    def test_criar_administrador(self):
        response = self.client.post(reverse('administrador_novo'), {
            'first_name': 'Novo',
            'last_name': 'Admin',
            'username': 'novo_admin',
            'email': 'novo@example.com',
            'password': 'senha123',
        })

        self.assertRedirects(response, reverse('administrador_lista'))
        novo = User.objects.get(username='novo_admin')
        self.assertTrue(novo.groups.filter(name='Administrador').exists())

    def test_criar_administrador_username_duplicado_mostra_erro(self):
        response = self.client.post(reverse('administrador_novo'), {
            'first_name': 'Duplicado',
            'username': 'root',
            'password': 'senha123',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='root').count() > 1)

    def test_visualizar_administrador(self):
        alvo = User.objects.create_user(username='ver_admin', password='x', is_superuser=True)

        response = self.client.get(reverse('administrador_detalhe', args=[alvo.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ver_admin')

    def test_editar_administrador(self):
        alvo = User.objects.create_user(username='editar_admin', password='x', is_superuser=True)

        response = self.client.post(reverse('administrador_editar', args=[alvo.pk]), {
            'first_name': 'Editado',
            'last_name': 'Sobrenome',
            'email': 'editado@example.com',
            'ativo': 'on',
        })

        self.assertRedirects(response, reverse('administrador_lista'))
        alvo.refresh_from_db()
        self.assertEqual(alvo.first_name, 'Editado')

    def test_eliminar_administrador(self):
        alvo = User.objects.create_user(username='eliminar_admin', password='x', is_superuser=True)

        response = self.client.post(reverse('administrador_excluir', args=[alvo.pk]))

        self.assertRedirects(response, reverse('administrador_lista'))
        self.assertFalse(User.objects.filter(pk=alvo.pk).exists())

    def test_nao_pode_eliminar_a_propria_conta(self):
        response = self.client.post(reverse('administrador_excluir', args=[self.superuser.pk]))

        self.assertRedirects(response, reverse('administrador_lista'))
        self.assertTrue(User.objects.filter(pk=self.superuser.pk).exists())
