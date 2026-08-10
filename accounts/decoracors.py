from functools import wraps

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from .utils import (
    eh_subdiretor_pedagogico,
    eh_admin_ou_professor,
    eh_aluno,
    eh_encarregado,
    eh_professor,
    eh_diretor_geral,
    eh_chefe_secretaria,
    eh_coordenador_turno,
    eh_coordenador_pais_encarregados,
)


def grupo_requerido(nome_grupo):

    return user_passes_test(
        lambda u: u.groups.filter(
            name=nome_grupo
        ).exists()
    )


def _acesso_requerido(teste):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not teste(request.user):
                return render(request, 'dashboards/sem_permissao.html', status=403)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def subdiretor_pedagogico_requerido(view_func):
    return _acesso_requerido(eh_subdiretor_pedagogico)(view_func)


def professor_requerido(view_func):
    return _acesso_requerido(eh_professor)(view_func)


def admin_ou_professor_requerido(view_func):
    return _acesso_requerido(eh_admin_ou_professor)(view_func)


def aluno_requerido(view_func):
    return _acesso_requerido(eh_aluno)(view_func)


def encarregado_requerido(view_func):
    return _acesso_requerido(eh_encarregado)(view_func)


def diretor_geral_requerido(view_func):
    return _acesso_requerido(eh_diretor_geral)(view_func)


def chefe_secretaria_requerido(view_func):
    return _acesso_requerido(eh_chefe_secretaria)(view_func)


def coordenador_turno_requerido(view_func):
    return _acesso_requerido(eh_coordenador_turno)(view_func)


def coordenador_pais_requerido(view_func):
    return _acesso_requerido(eh_coordenador_pais_encarregados)(view_func)