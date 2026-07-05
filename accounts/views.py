from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.forms import AuthenticationForm
from .models import Perfil
from django.contrib.auth.decorators import login_required
from .utils import usuario_do_grupo, eh_administrador
from alunos.models import Aluno, Encarregado
from professores.models import Professor, AtribuicaoDocente
from turmas.models import Turma, Classe, PeriodoAcademico
from disciplinas.models import Disciplina
from pautas.models import Avaliacao, ResultadoDisciplina
from pautas.services.dashboard_aluno import estatisticas_aluno

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
    context = {
        'total_alunos': Aluno.objects.count(),
        'total_professores': Professor.objects.count(),
        'total_turmas': Turma.objects.count(),
        'total_disciplinas': Disciplina.objects.count(),
        'total_encarregados': Encarregado.objects.count(),
    }

    if eh_administrador(user):

        avaliacoes_pendentes = Avaliacao.objects.filter(
            status=Avaliacao.STATUS_RASCUNHO
        ).count()
        avaliacoes_com_erros = Avaliacao.objects.filter(
            status=Avaliacao.STATUS_COM_ERROS
        ).count()
        avaliacoes_validadas = Avaliacao.objects.filter(
            status=Avaliacao.STATUS_VALIDADA
        ).count()

        resultados_pendentes = ResultadoDisciplina.objects.exclude(
            status=ResultadoDisciplina.STATUS_VALIDADA
        ).count()
        resultados_validados = ResultadoDisciplina.objects.filter(
            status=ResultadoDisciplina.STATUS_VALIDADA
        ).count()

        turmas_por_classe = (
            Classe.objects
            .order_by('nome')
            .values_list('nome', flat=True)
        )
        contagem_por_classe = [
            Turma.objects.filter(classe__nome=nome, ativo=True).count()
            for nome in turmas_por_classe
        ]

        context.update({
            'avaliacoes_pendentes': avaliacoes_pendentes,
            'avaliacoes_com_erros': avaliacoes_com_erros,
            'avaliacoes_validadas': avaliacoes_validadas,
            'resultados_pendentes': resultados_pendentes,
            'resultados_validados': resultados_validados,
            'periodos': PeriodoAcademico.objects.select_related('ano_letivo').order_by(
                '-ano_letivo__descricao', 'nome'
            ),
            'grafico_avaliacoes_labels': ['Rascunho', 'Com Erros', 'Validadas'],
            'grafico_avaliacoes_dados': [
                avaliacoes_pendentes, avaliacoes_com_erros, avaliacoes_validadas
            ],
            'grafico_turmas_labels': list(turmas_por_classe),
            'grafico_turmas_dados': contagem_por_classe,
        })

        return render(
            request,
            'dashboards/admin.html',
            context
        )

    if usuario_do_grupo(user, 'Professor'):

        atribuicoes_professor = AtribuicaoDocente.objects.filter(professor__user=user)

        context.update({
            'total_turmas': atribuicoes_professor.values('turma').distinct().count(),
            'total_disciplinas': atribuicoes_professor.values('disciplina').distinct().count(),
            'avaliacoes_pendentes': Avaliacao.objects.filter(
                atribuicao__professor__user=user, status=Avaliacao.STATUS_RASCUNHO
            ).count(),
            'avaliacoes_com_erros': Avaliacao.objects.filter(
                atribuicao__professor__user=user, status=Avaliacao.STATUS_COM_ERROS
            ).count(),
            'avaliacoes_validadas': Avaliacao.objects.filter(
                atribuicao__professor__user=user, status=Avaliacao.STATUS_VALIDADA
            ).count(),
        })

        return render(
            request,
            'dashboards/professor.html', context
        )

    if usuario_do_grupo(user, 'Aluno'):

        aluno = getattr(user, 'aluno', None)

        context.update({'aluno': aluno})

        if aluno:
            context.update(estatisticas_aluno(aluno))
            context['resultados_validados'] = len(context['resultados'])
        else:
            context['resultados_validados'] = 0

        return render(
            request,
            'dashboards/aluno.html',
            context
        )

    if usuario_do_grupo(user, 'Encarregado'):

        encarregado = getattr(user, 'encarregado', None)

        context.update({
            'dependentes': (
                Aluno.objects.filter(encarregado=encarregado).order_by('nome')
                if encarregado else Aluno.objects.none()
            ),
        })

        return render(
            request,
            'dashboards/encarregado.html',
            context
        )

    return render(
        request,
        'dashboards/sem_permissao.html'
    )
