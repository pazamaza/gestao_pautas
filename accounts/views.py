from django import forms
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth import logout
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from .models import Perfil
from django.contrib.auth.decorators import login_required
from .utils import usuario_do_grupo, eh_administrador
from alunos.models import Aluno, Encarregado
from professores.models import Professor, AtribuicaoDocente
from turmas.models import Turma, Classe, PeriodoAcademico, AnoLetivo
from disciplinas.models import Disciplina
from pautas.models import Avaliacao, ResultadoDisciplina
from pautas.services.dashboard_aluno import estatisticas_aluno


class DadosPessoaisForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

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

        atribuicoes_professor = AtribuicaoDocente.objects.filter(
            professor__user=user, ativo=True
        ).select_related('turma', 'disciplina', 'ano_letivo')

        turmas_ids = list(atribuicoes_professor.values_list('turma_id', flat=True).distinct())
        disciplinas_ids = list(atribuicoes_professor.values_list('disciplina_id', flat=True).distinct())

        avaliacoes_pendentes = Avaliacao.objects.filter(
            atribuicao__professor__user=user, status=Avaliacao.STATUS_RASCUNHO
        ).count()
        avaliacoes_com_erros = Avaliacao.objects.filter(
            atribuicao__professor__user=user, status=Avaliacao.STATUS_COM_ERROS
        ).count()
        avaliacoes_validadas = Avaliacao.objects.filter(
            atribuicao__professor__user=user, status=Avaliacao.STATUS_VALIDADA
        ).count()

        ano_letivo_ativo = AnoLetivo.objects.filter(ativo=True).first()
        resultados_professor = ResultadoDisciplina.objects.filter(
            disciplina_id__in=disciplinas_ids,
            aluno__turma_id__in=turmas_ids,
            ano_letivo=ano_letivo_ativo,
        ).select_related('aluno__turma')

        medias_por_turma = {}
        for resultado in resultados_professor:
            medias_por_turma.setdefault(str(resultado.aluno.turma), []).append(float(resultado.mf))

        aprovados = sum(
            1 for r in resultados_professor if r.resultado == ResultadoDisciplina.RESULTADO_APROVADO
        )
        reprovados = sum(
            1 for r in resultados_professor if r.resultado == ResultadoDisciplina.RESULTADO_REPROVADO
        )

        atribuicao_padrao = atribuicoes_professor.order_by(
            'turma__classe__nome', 'turma__nome', 'disciplina__nome'
        ).first()

        context.update({
            'total_turmas': len(turmas_ids),
            'total_disciplinas': len(disciplinas_ids),
            'total_alunos': Aluno.objects.filter(
                turma_id__in=turmas_ids, estado=Aluno.ESTADO_ATIVO
            ).distinct().count(),
            'pautas_por_finalizar': avaliacoes_pendentes + avaliacoes_com_erros,
            'avaliacoes_pendentes': avaliacoes_pendentes,
            'avaliacoes_com_erros': avaliacoes_com_erros,
            'avaliacoes_validadas': avaliacoes_validadas,
            'atribuicao_padrao': atribuicao_padrao,
            'grafico_medias_labels': list(medias_por_turma.keys()),
            'grafico_medias_dados': [
                round(sum(valores) / len(valores), 1) for valores in medias_por_turma.values()
            ],
            'grafico_resultado_labels': ['Aprovados', 'Reprovados'],
            'grafico_resultado_dados': [aprovados, reprovados],
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


@login_required
def perfil(request):

    dados_form = DadosPessoaisForm(instance=request.user)
    senha_form = PasswordChangeForm(user=request.user)

    if request.method == 'POST':
        if 'salvar_dados' in request.POST:
            dados_form = DadosPessoaisForm(request.POST, instance=request.user)
            if dados_form.is_valid():
                dados_form.save()
                messages.success(request, 'Dados atualizados com sucesso.')
                return redirect('perfil')
        elif 'alterar_senha' in request.POST:
            senha_form = PasswordChangeForm(user=request.user, data=request.POST)
            if senha_form.is_valid():
                user = senha_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password alterada com sucesso.')
                return redirect('perfil')

    for campo in senha_form.fields.values():
        campo.widget.attrs['class'] = 'form-control'

    return render(
        request,
        'accounts/perfil.html',
        {'dados_form': dados_form, 'senha_form': senha_form},
    )
