from .models import Notificacao


def notificar_erro_pauta(professor_user, diretor_user, titulo, mensagem, link_url=''):
    destinatarios = {u for u in (professor_user, diretor_user) if u is not None}

    for destinatario in destinatarios:
        Notificacao.objects.create(
            destinatario=destinatario,
            titulo=titulo,
            mensagem=mensagem,
            nivel=Notificacao.NIVEL_ERRO,
            link_url=link_url,
        )
