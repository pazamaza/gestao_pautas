from .utils import eh_administrador, eh_aluno, eh_encarregado, eh_professor


def papel_usuario(request):
    if not request.user.is_authenticated:
        return {}

    contexto = {
        'eh_administrador_nav': eh_administrador(request.user),
        'eh_professor_nav': eh_professor(request.user),
        'eh_aluno_nav': eh_aluno(request.user),
        'eh_encarregado_nav': eh_encarregado(request.user),
    }

    if contexto['eh_professor_nav']:
        from professores.models import AtribuicaoDocente
        from turmas.models import Turma
        turmas_ids = AtribuicaoDocente.objects.filter(
            professor__user=request.user, ativo=True
        ).values_list('turma_id', flat=True)
        contexto['turmas_professor_nav'] = Turma.objects.filter(
            id__in=turmas_ids
        ).order_by('classe__nome', 'nome')

    return contexto
