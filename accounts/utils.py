def usuario_do_grupo(user, grupo):

    return user.groups.filter(
        name=grupo
    ).exists()


def eh_subdiretor_pedagogico(user):
    return user.is_superuser or usuario_do_grupo(user, 'Sub-diretor Pedagógico')


def eh_professor(user):
    return usuario_do_grupo(user, 'Professor')


def eh_admin_ou_professor(user):
    return eh_subdiretor_pedagogico(user) or eh_professor(user)


def eh_aluno(user):
    return usuario_do_grupo(user, 'Aluno')


def eh_encarregado(user):
    return usuario_do_grupo(user, 'Encarregado')


def eh_diretor_geral(user):
    return user.is_superuser or usuario_do_grupo(user, 'Diretor Geral do Complexo')


def eh_chefe_secretaria(user):
    return usuario_do_grupo(user, 'Chefe de Secretaria')


def eh_coordenador_turno(user):
    return usuario_do_grupo(user, 'Coordenador de Turno')


def eh_coordenador_pais_encarregados(user):
    return usuario_do_grupo(user, 'Coordenador de Pais e Encarregados de Educação')