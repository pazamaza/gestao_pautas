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


def notificar(destinatarios, titulo, mensagem, nivel=Notificacao.NIVEL_INFO, link_url=''):
    usuarios = {u for u in destinatarios if u is not None}

    for destinatario in usuarios:
        Notificacao.objects.create(
            destinatario=destinatario,
            titulo=titulo,
            mensagem=mensagem,
            nivel=nivel,
            link_url=link_url,
        )
