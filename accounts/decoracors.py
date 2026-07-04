from functools import wraps

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from .utils import (
    eh_administrador,
    eh_admin_ou_professor,
    eh_aluno,
    eh_encarregado,
    eh_professor,
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


def administrador_requerido(view_func):
    return _acesso_requerido(eh_administrador)(view_func)


def professor_requerido(view_func):
    return _acesso_requerido(eh_professor)(view_func)


def admin_ou_professor_requerido(view_func):
    return _acesso_requerido(eh_admin_ou_professor)(view_func)


def aluno_requerido(view_func):
    return _acesso_requerido(eh_aluno)(view_func)


def encarregado_requerido(view_func):
    return _acesso_requerido(eh_encarregado)(view_func)