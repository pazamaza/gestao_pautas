def usuario_do_grupo(user, grupo):

    return user.groups.filter(
        name=grupo
    ).exists()


def eh_administrador(user):
    return user.is_superuser or usuario_do_grupo(user, 'Administrador')


def eh_professor(user):
    return usuario_do_grupo(user, 'Professor')


def eh_admin_ou_professor(user):
    return eh_administrador(user) or eh_professor(user)


def eh_aluno(user):
    return usuario_do_grupo(user, 'Aluno')


def eh_encarregado(user):
    return usuario_do_grupo(user, 'Encarregado')