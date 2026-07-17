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
from professores.models import Professor, AtribuicaoDocente, DiretorTurma
from turmas.models import Turma, PeriodoAcademico, AnoLetivo
from disciplinas.models import Disciplina
from frequencias.models import Frequencia, JustificacaoFalta
from pautas.models import Avaliacao, Nota, PedidoDocumento, ResultadoDisciplina
from pautas.services.dashboard_aluno import estatisticas_aluno


def _media(valores):
    valores = list(valores)
    if not valores:
        return None
    return round(sum(valores) / len(valores), 1)


def _situacao_nota(mt):
    if mt is None:
        return 'pendente'
    mt = float(mt)
    if mt < 8:
        return 'reprovado'
    if mt < 10:
        return 'exame'
    return 'aprovado'


def _contexto_dashboard_professor(request):
    user = request.user

    atribuicoes_professor = AtribuicaoDocente.objects.filter(
        professor__user=user, ativo=True
    ).select_related('turma__classe', 'disciplina', 'ano_letivo').order_by(
        'turma__classe__nome', 'turma__nome', 'disciplina__nome'
    )

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

    turmas_dirigidas = DiretorTurma.objects.filter(
        professor__user=user, ativo=True
    ).values_list('turma_id', flat=True)
    pedidos_boletim_pendentes = PedidoDocumento.objects.filter(
        status=PedidoDocumento.STATUS_PENDENTE,
        tipo=PedidoDocumento.TIPO_BOLETIM,
        aluno__turma_id__in=turmas_dirigidas,
    ).count()

    contexto = {
        'total_turmas': len(turmas_ids),
        'total_disciplinas': len(disciplinas_ids),
        'total_alunos': Aluno.objects.filter(
            turma_id__in=turmas_ids, estado=Aluno.ESTADO_ATIVO
        ).distinct().count(),
        'pautas_por_finalizar': avaliacoes_pendentes + avaliacoes_com_erros,
        'avaliacoes_pendentes': avaliacoes_pendentes,
        'avaliacoes_com_erros': avaliacoes_com_erros,
        'avaliacoes_validadas': avaliacoes_validadas,
        'atribuicoes_professor': atribuicoes_professor,
        'eh_diretor_turma': turmas_dirigidas.exists(),
        'pedidos_boletim_pendentes': pedidos_boletim_pendentes,
    }

    if not atribuicoes_professor.exists():
        contexto.update({
            'atribuicao_padrao': None,
            'atribuicao_selecionada': None,
        })
        return contexto

    turma_id = request.GET.get('turma')
    disciplina_id = request.GET.get('disciplina')

    atribuicao_selecionada = None
    if turma_id and disciplina_id:
        atribuicao_selecionada = atribuicoes_professor.filter(
            turma_id=turma_id, disciplina_id=disciplina_id
        ).first()
    if not atribuicao_selecionada:
        atribuicao_selecionada = atribuicoes_professor.first()

    contexto['atribuicao_padrao'] = atribuicao_selecionada
    contexto['atribuicao_selecionada'] = atribuicao_selecionada

    periodos_disponiveis = PeriodoAcademico.objects.filter(
        ano_letivo=atribuicao_selecionada.ano_letivo
    ).order_by('id')
    periodo_id = request.GET.get('periodo')
    periodo_selecionado = (
        periodos_disponiveis.filter(pk=periodo_id).first() if periodo_id else None
    ) or periodos_disponiveis.filter(aberto=True).first() or periodos_disponiveis.first()

    contexto['periodos_disponiveis'] = periodos_disponiveis
    contexto['periodo_selecionado'] = periodo_selecionado

    alunos_turma = Aluno.objects.filter(
        turma=atribuicao_selecionada.turma, estado=Aluno.ESTADO_ATIVO
    ).select_related('encarregado').order_by('nome')
    contexto['alunos_turma'] = alunos_turma

    avaliacao_atual = None
    if periodo_selecionado:
        avaliacao_atual = Avaliacao.objects.filter(
            atribuicao=atribuicao_selecionada, periodo=periodo_selecionado
        ).first()

    notas_periodo_atual = {}
    if avaliacao_atual:
        for nota in Nota.objects.filter(avaliacao=avaliacao_atual, aluno__in=alunos_turma):
            notas_periodo_atual[nota.aluno_id] = nota

    notas_historico = Nota.objects.filter(
        avaliacao__atribuicao=atribuicao_selecionada, aluno__in=alunos_turma
    ).select_related('avaliacao__periodo').order_by('avaliacao__periodo_id')
    tendencia_por_aluno = {}
    for nota in notas_historico:
        tendencia_por_aluno.setdefault(nota.aluno_id, []).append(float(nota.mt))

    frequencias_atribuicao = Frequencia.objects.filter(
        atribuicao=atribuicao_selecionada, aluno__in=alunos_turma
    )
    total_freq_por_aluno = {}
    presentes_freq_por_aluno = {}
    for frequencia in frequencias_atribuicao:
        total_freq_por_aluno[frequencia.aluno_id] = total_freq_por_aluno.get(frequencia.aluno_id, 0) + 1
        if frequencia.estado in (Frequencia.PRESENTE, Frequencia.ATRASO):
            presentes_freq_por_aluno[frequencia.aluno_id] = presentes_freq_por_aluno.get(frequencia.aluno_id, 0) + 1

    linhas_turma = []
    contagem_situacao = {'aprovado': 0, 'exame': 0, 'reprovado': 0}
    for aluno in alunos_turma:
        nota = notas_periodo_atual.get(aluno.id)
        situacao = _situacao_nota(nota.mt if nota else None)
        if situacao in contagem_situacao:
            contagem_situacao[situacao] += 1

        total_freq = total_freq_por_aluno.get(aluno.id, 0)
        presentes_freq = presentes_freq_por_aluno.get(aluno.id, 0)

        linhas_turma.append({
            'aluno': aluno,
            'nota': nota,
            'situacao': situacao,
            'tendencia': tendencia_por_aluno.get(aluno.id, []),
            'frequencia_pct': round(presentes_freq / total_freq * 100, 1) if total_freq else None,
        })

    total_frequencias = sum(total_freq_por_aluno.values())
    total_presentes = sum(presentes_freq_por_aluno.values())
    frequencia_media_turma = (
        round(total_presentes / total_frequencias * 100, 1) if total_frequencias else None
    )

    desempenho_turma = _media(float(n.mt) for n in notas_periodo_atual.values())

    notas_a_lancar = alunos_turma.count() - len(notas_periodo_atual)
    justificacoes_pendentes = JustificacaoFalta.objects.filter(
        frequencia__atribuicao=atribuicao_selecionada, aprovada=False
    ).count()

    total_classificados = sum(contagem_situacao.values())

    contexto.update({
        'linhas_turma': linhas_turma,
        'frequencia_media_turma': frequencia_media_turma,
        'desempenho_turma': desempenho_turma,
        'notas_a_lancar': notas_a_lancar,
        'justificacoes_pendentes': justificacoes_pendentes,
        'distribuicao_situacao': contagem_situacao,
        'distribuicao_situacao_pct': {
            chave: round(valor / total_classificados * 100, 1) if total_classificados else 0
            for chave, valor in contagem_situacao.items()
        },
        'avaliacao_atual': avaliacao_atual,
    })

    return contexto


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

        anos_letivos = AnoLetivo.objects.all()
        ano_letivo_id = request.GET.get('ano_letivo')
        ano_letivo_selecionado = (
            anos_letivos.filter(pk=ano_letivo_id).first() if ano_letivo_id
            else anos_letivos.filter(ativo=True).first() or anos_letivos.first()
        )

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

        resultados = (
            ResultadoDisciplina.objects
            .filter(ano_letivo=ano_letivo_selecionado)
            .select_related('aluno', 'aluno__turma', 'disciplina')
            if ano_letivo_selecionado else ResultadoDisciplina.objects.none()
        )
        resultados_com_notas = [r for r in resultados if r.mf and r.mf > 0]

        aprovados = sum(
            1 for r in resultados_com_notas if r.resultado == ResultadoDisciplina.RESULTADO_APROVADO
        )
        reprovados = sum(
            1 for r in resultados_com_notas
            if r.resultado in (ResultadoDisciplina.RESULTADO_REPROVADO, ResultadoDisciplina.RESULTADO_DEFICIENCIA)
        )
        total_avaliados = len(resultados_com_notas)
        taxa_aprovacao = round(aprovados / total_avaliados * 100, 1) if total_avaliados else 0
        taxa_reprovacao = round(reprovados / total_avaliados * 100, 1) if total_avaliados else 0
        media_geral = _media(r.mf for r in resultados_com_notas)

        evolucao_labels = ['1º Trimestre', '2º Trimestre', '3º Trimestre']
        evolucao_dados = [
            _media(float(r.mt1) for r in resultados_com_notas if r.mt1 and r.mt1 > 0) or 0,
            _media(float(r.mt2) for r in resultados_com_notas if r.mt2 and r.mt2 > 0) or 0,
            _media(float(r.mt3) for r in resultados_com_notas if r.mt3 and r.mt3 > 0) or 0,
        ]

        distribuicao_resultados = {}
        for r in resultados_com_notas:
            distribuicao_resultados[r.resultado] = distribuicao_resultados.get(r.resultado, 0) + 1

        por_disciplina = {}
        for r in resultados_com_notas:
            por_disciplina.setdefault(r.disciplina.nome, []).append(float(r.mf))
        disciplina_labels = sorted(por_disciplina.keys())
        disciplina_dados = [_media(por_disciplina[nome]) for nome in disciplina_labels]

        por_turma = {}
        for r in resultados_com_notas:
            por_turma.setdefault(str(r.aluno.turma), []).append(float(r.mf))
        top_turmas = sorted(
            ((nome, _media(valores)) for nome, valores in por_turma.items()),
            key=lambda item: item[1], reverse=True,
        )[:5]

        medias_por_aluno = {}
        for r in resultados_com_notas:
            medias_por_aluno.setdefault(r.aluno, []).append(float(r.mf))

        alunos_risco = sorted(
            (
                {'aluno': aluno, 'turma': aluno.turma, 'media': _media(valores)}
                for aluno, valores in medias_por_aluno.items()
                if _media(valores) is not None and _media(valores) < 10
            ),
            key=lambda item: item['media'],
        )[:5]

        melhores_medias = sorted(
            (
                {'aluno': aluno, 'turma': aluno.turma, 'media': _media(valores)}
                for aluno, valores in medias_por_aluno.items()
            ),
            key=lambda item: item['media'],
            reverse=True,
        )[:5]

        sexos = Aluno.objects.filter(estado=Aluno.ESTADO_ATIVO).values_list('sexo', flat=True)
        total_feminino = sum(1 for sexo in sexos if sexo == 'F')
        total_masculino = sum(1 for sexo in sexos if sexo == 'M')

        frequencias_ano = (
            Frequencia.objects.filter(atribuicao__ano_letivo=ano_letivo_selecionado)
            if ano_letivo_selecionado else Frequencia.objects.none()
        )
        meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        total_por_mes = {}
        presentes_por_mes = {}
        for frequencia in frequencias_ano:
            mes = frequencia.data.month
            total_por_mes[mes] = total_por_mes.get(mes, 0) + 1
            if frequencia.estado in (Frequencia.PRESENTE, Frequencia.ATRASO):
                presentes_por_mes[mes] = presentes_por_mes.get(mes, 0) + 1
        meses_com_dados = sorted(total_por_mes.keys())

        context.update({
            'total_alunos': Aluno.objects.filter(estado=Aluno.ESTADO_ATIVO).count(),
            'total_turmas': Turma.objects.filter(ativo=True).count(),
            'anos_letivos': anos_letivos,
            'ano_letivo_selecionado': ano_letivo_selecionado,
            'media_geral': media_geral,
            'taxa_aprovacao': taxa_aprovacao,
            'taxa_reprovacao': taxa_reprovacao,
            'avaliacoes_pendentes': avaliacoes_pendentes,
            'avaliacoes_com_erros': avaliacoes_com_erros,
            'avaliacoes_validadas': avaliacoes_validadas,
            'resultados_pendentes': resultados_pendentes,
            'resultados_validados': resultados_validados,
            'periodos': PeriodoAcademico.objects.select_related('ano_letivo').order_by(
                '-ano_letivo__descricao', 'nome'
            ),
            'alunos_risco': alunos_risco,
            'melhores_medias': melhores_medias,
            'evolucao_labels': evolucao_labels,
            'evolucao_dados': evolucao_dados,
            'resultado_labels': list(distribuicao_resultados.keys()),
            'resultado_dados': list(distribuicao_resultados.values()),
            'disciplina_labels': disciplina_labels,
            'disciplina_dados': disciplina_dados,
            'turma_labels': [item[0] for item in top_turmas],
            'turma_dados': [item[1] for item in top_turmas],
            'genero_labels': ['Feminino', 'Masculino'],
            'genero_dados': [total_feminino, total_masculino],
            'frequencia_labels': [meses_nomes[mes - 1] for mes in meses_com_dados],
            'frequencia_dados': [
                round(presentes_por_mes.get(mes, 0) / total_por_mes[mes] * 100, 1)
                for mes in meses_com_dados
            ],
            'pedidos_documentos_pendentes': PedidoDocumento.objects.filter(
                status=PedidoDocumento.STATUS_PENDENTE
            ).count(),
            'pedidos_pagamento_pendentes': PedidoDocumento.objects.filter(
                status=PedidoDocumento.STATUS_PAGAMENTO_SUBMETIDO
            ).count(),
        })

        return render(
            request,
            'dashboards/admin.html',
            context
        )

    if usuario_do_grupo(user, 'Professor'):

        context.update(_contexto_dashboard_professor(request))

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
