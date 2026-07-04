from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Notificacao
from .services import notificar_erro_pauta


class NotificarErroPautaTests(TestCase):
    def setUp(self):
        self.professor_user = User.objects.create_user(username='prof', password='senha123')
        self.diretor_user = User.objects.create_user(username='diretor', password='senha123')

    def test_cria_notificacao_para_ambos_destinatarios(self):
        notificar_erro_pauta(
            professor_user=self.professor_user,
            diretor_user=self.diretor_user,
            titulo='Erro na pauta',
            mensagem='Verifique a nota do aluno X.',
            link_url='/pautas/avaliacoes/1/pauta/',
        )

        self.assertEqual(Notificacao.objects.count(), 2)
        self.assertTrue(
            Notificacao.objects.filter(destinatario=self.professor_user).exists()
        )
        self.assertTrue(
            Notificacao.objects.filter(destinatario=self.diretor_user).exists()
        )

    def test_nao_duplica_quando_professor_e_diretor_sao_o_mesmo(self):
        notificar_erro_pauta(
            professor_user=self.professor_user,
            diretor_user=self.professor_user,
            titulo='Erro na pauta',
            mensagem='Verifique a nota do aluno X.',
        )

        self.assertEqual(Notificacao.objects.count(), 1)

    def test_ignora_destinatario_ausente(self):
        notificar_erro_pauta(
            professor_user=self.professor_user,
            diretor_user=None,
            titulo='Erro na pauta',
            mensagem='Sem diretor definido.',
        )

        self.assertEqual(Notificacao.objects.count(), 1)


class NotificacaoInboxTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='prof', password='senha123')
        self.outro_user = User.objects.create_user(username='outro', password='senha123')

        Notificacao.objects.create(
            destinatario=self.user, titulo='Minha notificação', mensagem='Olá'
        )
        Notificacao.objects.create(
            destinatario=self.outro_user, titulo='Notificação de outro', mensagem='Oi'
        )

    def test_lista_mostra_apenas_notificacoes_do_proprio_utilizador(self):
        self.client.login(username='prof', password='senha123')
        response = self.client.get(reverse('notificacao_lista'))

        self.assertContains(response, 'Minha notificação')
        self.assertNotContains(response, 'Notificação de outro')

    def test_marcar_lida(self):
        notificacao = Notificacao.objects.get(destinatario=self.user)
        self.client.login(username='prof', password='senha123')
        self.client.post(reverse('notificacao_marcar_lida', args=[notificacao.pk]))

        notificacao.refresh_from_db()
        self.assertTrue(notificacao.lida)
