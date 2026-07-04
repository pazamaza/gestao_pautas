from .utils import eh_administrador, eh_professor


def papel_usuario(request):
    if not request.user.is_authenticated:
        return {}

    return {
        'eh_administrador_nav': eh_administrador(request.user),
        'eh_professor_nav': eh_professor(request.user),
    }
