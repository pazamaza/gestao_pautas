def usuario_do_grupo(user, grupo):

    return user.groups.filter(
        name=grupo
    ).exists()