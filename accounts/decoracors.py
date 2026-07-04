from django.contrib.auth.decorators import user_passes_test


def grupo_requerido(nome_grupo):

    return user_passes_test(
        lambda u: u.groups.filter(
            name=nome_grupo
        ).exists()
    )