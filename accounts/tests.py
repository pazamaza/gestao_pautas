from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .utils import (
    eh_subdiretor_pedagogico,
    eh_professor,
    eh_diretor_geral,
    eh_chefe_secretaria,
    eh_coordenador_turno,
    eh_coordenador_pais_encarregados,
)


class PapeisUsuarioTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Sub-diretor Pedagógico')
        Group.objects.get_or_create(name='Professor')

    def test_superuser_eh_subdiretor_pedagogico_sem_grupo(self):
        user = User.objects.create_user(username='super', password='x', is_superuser=True)
        self.assertTrue(eh_subdiretor_pedagogico(user))

    def test_usuario_no_grupo_subdiretor_pedagogico_eh_subdiretor_pedagogico(self):
        user = User.objects.create_user(username='adm', password='x')
        user.groups.add(Group.objects.get(name='Sub-diretor Pedagógico'))
        self.assertTrue(eh_subdiretor_pedagogico(user))

    def test_usuario_sem_grupo_nao_eh_subdiretor_pedagogico_nem_professor(self):
        user = User.objects.create_user(username='comum', password='x')
        self.assertFalse(eh_subdiretor_pedagogico(user))
        self.assertFalse(eh_professor(user))


class DashboardViewTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Sub-diretor Pedagógico')

    def test_dashboard_admin_renderiza_template_admin(self):
        user = User.objects.create_user(username='adm', password='senha123')
        user.groups.add(Group.objects.get(name='Sub-diretor Pedagógico'))
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


class SubdiretorPedagogicoCrudTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Sub-diretor Pedagógico')
        self.superuser = User.objects.create_superuser(
            username='root', password='senha123', email='root@example.com'
        )
        self.client.login(username='root', password='senha123')

    def test_subdiretor_pedagogico_do_grupo_sem_superuser_nao_acede(self):
        user = User.objects.create_user(username='adm_comum', password='senha123')
        user.groups.add(Group.objects.get(name='Sub-diretor Pedagógico'))
        self.client.logout()
        self.client.login(username='adm_comum', password='senha123')

        response = self.client.get(reverse('subdiretor_pedagogico_lista'))

        self.assertEqual(response.status_code, 403)

    def test_lista_subdiretores_pedagogicos_inclui_superuser(self):
        response = self.client.get(reverse('subdiretor_pedagogico_lista'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'root')

    def test_criar_subdiretor_pedagogico(self):
        response = self.client.post(reverse('subdiretor_pedagogico_novo'), {
            'first_name': 'Novo',
            'last_name': 'Admin',
            'username': 'novo_admin',
            'email': 'novo@example.com',
            'password': 'senha123',
        })

        self.assertRedirects(response, reverse('subdiretor_pedagogico_lista'))
        novo = User.objects.get(username='novo_admin')
        self.assertTrue(novo.groups.filter(name='Sub-diretor Pedagógico').exists())

    def test_criar_subdiretor_pedagogico_username_duplicado_mostra_erro(self):
        response = self.client.post(reverse('subdiretor_pedagogico_novo'), {
            'first_name': 'Duplicado',
            'username': 'root',
            'password': 'senha123',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='root').count() > 1)

    def test_visualizar_subdiretor_pedagogico(self):
        alvo = User.objects.create_user(username='ver_admin', password='x', is_superuser=True)

        response = self.client.get(reverse('subdiretor_pedagogico_detalhe', args=[alvo.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ver_admin')

    def test_editar_subdiretor_pedagogico(self):
        alvo = User.objects.create_user(username='editar_admin', password='x', is_superuser=True)

        response = self.client.post(reverse('subdiretor_pedagogico_editar', args=[alvo.pk]), {
            'first_name': 'Editado',
            'last_name': 'Sobrenome',
            'email': 'editado@example.com',
            'ativo': 'on',
        })

        self.assertRedirects(response, reverse('subdiretor_pedagogico_lista'))
        alvo.refresh_from_db()
        self.assertEqual(alvo.first_name, 'Editado')

    def test_eliminar_subdiretor_pedagogico(self):
        alvo = User.objects.create_user(username='eliminar_admin', password='x', is_superuser=True)

        response = self.client.post(reverse('subdiretor_pedagogico_excluir', args=[alvo.pk]))

        self.assertRedirects(response, reverse('subdiretor_pedagogico_lista'))
        self.assertFalse(User.objects.filter(pk=alvo.pk).exists())

    def test_nao_pode_eliminar_a_propria_conta(self):
        response = self.client.post(reverse('subdiretor_pedagogico_excluir', args=[self.superuser.pk]))

        self.assertRedirects(response, reverse('subdiretor_pedagogico_lista'))
        self.assertTrue(User.objects.filter(pk=self.superuser.pk).exists())


class NovosPapeisAdministrativosTests(TestCase):
    """Papéis administrativos acrescentados ao Complexo Escolar: Diretor
    Geral, Chefe de Secretaria, Coordenador de Turno e Coordenador de Pais
    e Encarregados de Educação. Cobre as funções eh_* e o CRUD genérico de
    conta (ContaAdministrativa*View)."""

    def setUp(self):
        for nome in [
            'Diretor Geral do Complexo',
            'Chefe de Secretaria',
            'Coordenador de Turno',
            'Coordenador de Pais e Encarregados de Educação',
        ]:
            Group.objects.get_or_create(name=nome)

    def test_superuser_eh_diretor_geral_sem_grupo(self):
        user = User.objects.create_user(username='super', password='x', is_superuser=True)
        self.assertTrue(eh_diretor_geral(user))

    def test_usuario_no_grupo_eh_o_papel_correspondente(self):
        casos = [
            ('Diretor Geral do Complexo', eh_diretor_geral),
            ('Chefe de Secretaria', eh_chefe_secretaria),
            ('Coordenador de Turno', eh_coordenador_turno),
            ('Coordenador de Pais e Encarregados de Educação', eh_coordenador_pais_encarregados),
        ]
        for grupo_nome, checador in casos:
            with self.subTest(grupo=grupo_nome):
                user = User.objects.create_user(username=f'u_{Group.objects.get(name=grupo_nome).pk}', password='x')
                user.groups.add(Group.objects.get(name=grupo_nome))
                self.assertTrue(checador(user))

    def test_usuario_comum_nao_eh_nenhum_dos_novos_papeis(self):
        user = User.objects.create_user(username='comum2', password='x')
        self.assertFalse(eh_diretor_geral(user))
        self.assertFalse(eh_chefe_secretaria(user))
        self.assertFalse(eh_coordenador_turno(user))
        self.assertFalse(eh_coordenador_pais_encarregados(user))

    def test_dashboard_placeholder_por_papel(self):
        casos = [
            ('Chefe de Secretaria', 'dashboards/chefe_secretaria.html'),
            ('Coordenador de Turno', 'dashboards/coordenador_turno.html'),
            ('Coordenador de Pais e Encarregados de Educação', 'dashboards/coordenador_pais.html'),
        ]
        for grupo_nome, template in casos:
            with self.subTest(grupo=grupo_nome):
                user = User.objects.create_user(username=f'd_{Group.objects.get(name=grupo_nome).pk}', password='senha123')
                user.groups.add(Group.objects.get(name=grupo_nome))
                self.client.login(username=user.username, password='senha123')

                response = self.client.get(reverse('dashboard'))

                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)
                self.client.logout()

    def test_superuser_continua_a_ver_dashboard_admin_academico(self):
        # O superuser é simultaneamente Diretor Geral e Sub-diretor
        # Pedagógico; o dashboard académico (dashboards/admin.html) deve
        # continuar a ser o que é mostrado, para não quebrar o que já
        # funcionava antes destes 4 novos papéis.
        Group.objects.get_or_create(name='Sub-diretor Pedagógico')
        user = User.objects.create_user(username='super2', password='senha123', is_superuser=True)
        self.client.login(username='super2', password='senha123')

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboards/admin.html')


class DiretorGeralCrudTests(TestCase):
    """CRUD completo só é exercitado para um papel representativo
    (Diretor Geral, que tem a particularidade de incluir o superuser na
    listagem); os outros 3 papéis reaproveitam exatamente a mesma
    implementação genérica (ContaAdministrativa*View), só variando o
    grupo."""

    def setUp(self):
        Group.objects.get_or_create(name='Diretor Geral do Complexo')
        self.superuser = User.objects.create_superuser(
            username='root2', password='senha123', email='root2@example.com'
        )
        self.client.login(username='root2', password='senha123')

    def test_diretor_geral_do_grupo_sem_superuser_nao_acede_ao_crud(self):
        user = User.objects.create_user(username='dg_comum', password='senha123')
        user.groups.add(Group.objects.get(name='Diretor Geral do Complexo'))
        self.client.logout()
        self.client.login(username='dg_comum', password='senha123')

        response = self.client.get(reverse('diretor_geral_lista'))

        self.assertEqual(response.status_code, 403)

    def test_lista_diretores_gerais_inclui_superuser(self):
        response = self.client.get(reverse('diretor_geral_lista'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'root2')

    def test_criar_diretor_geral(self):
        response = self.client.post(reverse('diretor_geral_novo'), {
            'first_name': 'Novo',
            'last_name': 'Diretor',
            'username': 'novo_diretor_geral',
            'email': 'novo_dg@example.com',
            'password': 'senha123',
        })

        self.assertRedirects(response, reverse('diretor_geral_lista'))
        novo = User.objects.get(username='novo_diretor_geral')
        self.assertTrue(novo.groups.filter(name='Diretor Geral do Complexo').exists())

    def test_visualizar_e_editar_diretor_geral(self):
        alvo = User.objects.create_user(username='ver_dg', password='x')
        alvo.groups.add(Group.objects.get(name='Diretor Geral do Complexo'))

        resposta_ver = self.client.get(reverse('diretor_geral_detalhe', args=[alvo.pk]))
        self.assertEqual(resposta_ver.status_code, 200)

        resposta_editar = self.client.post(reverse('diretor_geral_editar', args=[alvo.pk]), {
            'first_name': 'Editado',
            'last_name': 'Sobrenome',
            'email': 'editado_dg@example.com',
            'ativo': 'on',
        })
        self.assertRedirects(resposta_editar, reverse('diretor_geral_lista'))
        alvo.refresh_from_db()
        self.assertEqual(alvo.first_name, 'Editado')

    def test_eliminar_diretor_geral(self):
        alvo = User.objects.create_user(username='eliminar_dg', password='x')
        alvo.groups.add(Group.objects.get(name='Diretor Geral do Complexo'))

        response = self.client.post(reverse('diretor_geral_excluir', args=[alvo.pk]))

        self.assertRedirects(response, reverse('diretor_geral_lista'))
        self.assertFalse(User.objects.filter(pk=alvo.pk).exists())

    def test_nao_pode_eliminar_a_propria_conta(self):
        response = self.client.post(reverse('diretor_geral_excluir', args=[self.superuser.pk]))

        self.assertRedirects(response, reverse('diretor_geral_lista'))
        self.assertTrue(User.objects.filter(pk=self.superuser.pk).exists())


class CoordenadorTurnoCrudTests(TestCase):
    """Fase 2: o cadastro de Coordenador de Turno grava o turno
    (Perfil.turno_coordenado) além dos campos genéricos de conta."""

    def setUp(self):
        Group.objects.get_or_create(name='Coordenador de Turno')
        self.superuser = User.objects.create_superuser(
            username='root3', password='senha123', email='root3@example.com'
        )
        self.client.login(username='root3', password='senha123')

    def test_criar_coordenador_turno_grava_turno_no_perfil(self):
        response = self.client.post(reverse('coordenador_turno_novo'), {
            'first_name': 'Novo',
            'last_name': 'Coordenador',
            'username': 'novo_coord_turno',
            'email': 'novo_ct@example.com',
            'password': 'senha123',
            'turno_coordenado': 'tarde',
        })

        self.assertRedirects(response, reverse('coordenador_turno_lista'))
        novo = User.objects.get(username='novo_coord_turno')
        self.assertTrue(novo.groups.filter(name='Coordenador de Turno').exists())
        self.assertEqual(novo.perfil.turno_coordenado, 'tarde')

    def test_editar_coordenador_turno_atualiza_turno(self):
        alvo = User.objects.create_user(username='editar_ct', password='x')
        alvo.groups.add(Group.objects.get(name='Coordenador de Turno'))
        alvo.perfil.turno_coordenado = 'manha'
        alvo.perfil.save()

        response = self.client.post(reverse('coordenador_turno_editar', args=[alvo.pk]), {
            'first_name': 'Editado',
            'last_name': 'Sobrenome',
            'email': 'editado_ct@example.com',
            'ativo': 'on',
            'turno_coordenado': 'noite',
        })

        self.assertRedirects(response, reverse('coordenador_turno_lista'))
        alvo.perfil.refresh_from_db()
        self.assertEqual(alvo.perfil.turno_coordenado, 'noite')


class CoordenadorTurnoDashboardTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Coordenador de Turno')

    def test_dashboard_mostra_turmas_do_turno(self):
        from turmas.models import AnoLetivo, Classe, Turma

        ano_letivo = AnoLetivo.objects.create(descricao='2026')
        classe = Classe.objects.create(nome='10ª Classe')
        Turma.objects.create(nome='A', classe=classe, ano_letivo=ano_letivo, periodo='tarde', ativo=True)
        Turma.objects.create(nome='B', classe=classe, ano_letivo=ano_letivo, periodo='manha', ativo=True)

        coordenador = User.objects.create_user(username='coord_turno_dash', password='senha123')
        coordenador.groups.add(Group.objects.get(name='Coordenador de Turno'))
        coordenador.perfil.turno_coordenado = 'tarde'
        coordenador.perfil.save()

        self.client.login(username='coord_turno_dash', password='senha123')
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboards/coordenador_turno.html')
        self.assertEqual(len(response.context['turmas_turno']), 1)
