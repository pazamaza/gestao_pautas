from .utils import eh_administrador, eh_aluno, eh_encarregado, eh_professor


def papel_usuario(request):
    if not request.user.is_authenticated:
        return {}

    return {
        'eh_administrador_nav': eh_administrador(request.user),
        'eh_professor_nav': eh_professor(request.user),
        'eh_aluno_nav': eh_aluno(request.user),
        'eh_encarregado_nav': eh_encarregado(request.user),
    }
