from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.forms import AuthenticationForm
from .models import Perfil
from django.contrib.auth.decorators import login_required
from .utils import usuario_do_grupo

def login_view(request):

    form = AuthenticationForm(
        request,
        data=request.POST or None
    )

    if form.is_valid():

        login(
            request,
            form.get_user()
        )

        return redirect('dashboard')

    return render(
        request,
        'accounts/login.html',
        {'form': form}
    )


def logout_view(request):

    logout(request)

    return redirect('home')


from django.contrib.auth.decorators import login_required


@login_required
def dashboard(request):

    user = request.user

    if user.is_superuser:

        return render(
            request,
            'dashboards/admin.html'
        )

    if usuario_do_grupo(user, 'Administrador'):

        return render(
            request,
            'dashboards/admin.html'
        )

    if usuario_do_grupo(user, 'Professor'):

        return render(
            request,
            'dashboards/professor.html'
        )

    if usuario_do_grupo(user, 'Aluno'):

        return render(
            request,
            'dashboards/aluno.html'
        )

    if usuario_do_grupo(user, 'Encarregado'):

        return render(
            request,
            'dashboards/encarregado.html'
        )

    return render(
        request,
        'dashboards/sem_permissao.html'
    )