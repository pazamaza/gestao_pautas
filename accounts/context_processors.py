from .utils import (
    eh_subdiretor_pedagogico,
    eh_aluno,
    eh_encarregado,
    eh_professor,
    eh_diretor_geral,
    eh_chefe_secretaria,
    eh_coordenador_turno,
    eh_coordenador_pais_encarregados,
)


def papel_usuario(request):
    if not request.user.is_authenticated:
        return {}

    contexto = {
        'eh_subdiretor_pedagogico_nav': eh_subdiretor_pedagogico(request.user),
        'eh_professor_nav': eh_professor(request.user),
        'eh_aluno_nav': eh_aluno(request.user),
        'eh_encarregado_nav': eh_encarregado(request.user),
        'eh_diretor_geral_nav': eh_diretor_geral(request.user),
        'eh_chefe_secretaria_nav': eh_chefe_secretaria(request.user),
        'eh_coordenador_turno_nav': eh_coordenador_turno(request.user),
        'eh_coordenador_pais_nav': eh_coordenador_pais_encarregados(request.user),
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
