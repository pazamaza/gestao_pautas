from django import forms
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth import logout
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import Group, User
from django.views import View
from django.views.generic import ListView, DetailView, DeleteView
from .forms import (
    SubdiretorPedagogicoCadastroForm,
    SubdiretorPedagogicoEdicaoForm,
    ContaAdministrativaCadastroForm,
    ContaAdministrativaEdicaoForm,
    CoordenadorTurnoCadastroForm,
    CoordenadorTurnoEdicaoForm,
)
from .mixins import SuperuserRequeridoMixin
from .models import Perfil
from django.contrib.auth.decorators import login_required
from .utils import (
    usuario_do_grupo,
    eh_subdiretor_pedagogico,
    eh_diretor_geral,
    eh_chefe_secretaria,
    eh_coordenador_turno,
    eh_coordenador_pais_encarregados,
)
from alunos.models import Aluno, Encarregado, Reclamacao
from professores.models import Professor, AtribuicaoDocente, DiretorTurma
from turmas.models import Turma, PeriodoAcademico, AnoLetivo
from disciplinas.models import Disciplina
from frequencias.models import Frequencia, JustificacaoFalta
from pautas.models import Avaliacao, Nota, PedidoDocumento, ResultadoDisciplina
from pautas.services.dashboard_aluno import (
    estatisticas_aluno, FREQUENCIA_MINIMA, MEDIA_MINIMA,
)


def _media(valores):
    valores = list(valores)
    if not valores:
        return None
    return round(sum(valores) / len(valores), 1)


def _frequencia_diaria(frequencias_queryset):
    """(labels, dados) de % de presença por dia, para os últimos 30 dias
    com registos — usado nos gráficos "Frequência Diária" dos dashboards
    da Secretaria e do Coordenador de Turno."""
    total_por_dia = {}
    presentes_por_dia = {}
    for f in frequencias_queryset:
        total_por_dia[f.data] = total_por_dia.get(f.data, 0) + 1
        if f.estado in (Frequencia.PRESENTE, Frequencia.ATRASO):
            presentes_por_dia[f.data] = presentes_por_dia.get(f.data, 0) + 1
    dias = sorted(total_por_dia.keys())[-30:]
    labels = [dia.strftime('%d/%m') for dia in dias]
    dados = [round(presentes_por_dia.get(dia, 0) / total_por_dia[dia] * 100, 1) for dia in dias]
    return labels, dados


def _situacao_nota(mt):
    if mt is None:
        return 'pendente'
    mt = float(mt)
    if mt < 8:
        return 'reprovado'
    if mt < 10:
        return 'exame'
    return 'aprovado'


def _contexto_estatisticas_academicas(request):
    """Estatísticas académicas completas (evolução, distribuição de
    resultados, desempenho por disciplina/turma, género, frequência
    mensal) — usado pelos dashboards do Sub-diretor Pedagógico e do
    Diretor Geral, que têm a mesma aparência visual (mesmos gráficos),
    só variando os cards extra de cada um."""

    anos_letivos = AnoLetivo.objects.all()
    ano_letivo_id = request.GET.get('ano_letivo')
    ano_letivo_selecionado = (
        anos_letivos.filter(pk=ano_letivo_id).first() if ano_letivo_id
        else anos_letivos.filter(ativo=True).first() or anos_letivos.first()
    )

    avaliacoes_pendentes = Avaliacao.objects.filter(status=Avaliacao.STATUS_RASCUNHO).count()
    avaliacoes_com_erros = Avaliacao.objects.filter(status=Avaliacao.STATUS_COM_ERROS).count()
    avaliacoes_validadas = Avaliacao.objects.filter(status=Avaliacao.STATUS_VALIDADA).count()

    resultados_pendentes = ResultadoDisciplina.objects.exclude(status=ResultadoDisciplina.STATUS_VALIDADA).count()
    resultados_validados = ResultadoDisciplina.objects.filter(status=ResultadoDisciplina.STATUS_VALIDADA).count()

    resultados = (
        ResultadoDisciplina.objects
        .filter(ano_letivo=ano_letivo_selecionado)
        .select_related('aluno', 'aluno__turma', 'disciplina')
        if ano_letivo_selecionado else ResultadoDisciplina.objects.none()
    )
    resultados_com_notas = [r for r in resultados if r.mf and r.mf > 0]

    aprovados = sum(1 for r in resultados_com_notas if r.resultado == ResultadoDisciplina.RESULTADO_APROVADO)
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

    return {
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
    }


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

    # Alunos em risco e justificações por decidir nas turmas que dirige
    # (só faz sentido calcular se for mesmo Diretor de Turma de alguma
    # turma — ver Fase 3, "Plano De Gestão de Responsabilidades").
    alunos_risco_turma_dirigida = []
    justificacoes_pendentes_turma_dirigida = 0
    if turmas_dirigidas:
        ano_letivo_atual = AnoLetivo.objects.filter(ativo=True).first() or AnoLetivo.objects.first()
        resultados_dirigidas = (
            ResultadoDisciplina.objects.filter(
                ano_letivo=ano_letivo_atual, aluno__turma_id__in=turmas_dirigidas,
            ).select_related('aluno', 'aluno__turma')
            if ano_letivo_atual else ResultadoDisciplina.objects.none()
        )
        medias_por_aluno_dirigida = {}
        for r in resultados_dirigidas:
            if r.mf and r.mf > 0:
                medias_por_aluno_dirigida.setdefault(r.aluno, []).append(float(r.mf))
        alunos_risco_turma_dirigida = sorted(
            (
                {'aluno': aluno, 'media': _media(valores)}
                for aluno, valores in medias_por_aluno_dirigida.items()
                if _media(valores) is not None and _media(valores) < 10
            ),
            key=lambda item: item['media'],
        )
        justificacoes_pendentes_turma_dirigida = JustificacaoFalta.objects.filter(
            frequencia__atribuicao__turma_id__in=turmas_dirigidas, aprovada=False,
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
        'alunos_risco_turma_dirigida': alunos_risco_turma_dirigida,
        'justificacoes_pendentes_turma_dirigida': justificacoes_pendentes_turma_dirigida,
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


@login_required
def dashboard(request):
    # Ponto de entrada único para os 4 perfis (Sub-diretor Pedagógico,
    # Professor, Aluno, Encarregado) — cada bloco 'if' monta o context e
    # escolhe o template do respectivo dashboard. Só um dos blocos é
    # executado por pedido, conforme o grupo do utilizador (ver
    # accounts/utils.py).

    user = request.user
    context = {
        'total_alunos': Aluno.objects.count(),
        'total_professores': Professor.objects.count(),
        'total_turmas': Turma.objects.count(),
        'total_disciplinas': Disciplina.objects.count(),
        'total_encarregados': Encarregado.objects.count(),
    }

    if eh_subdiretor_pedagogico(user) and not eh_diretor_geral(user):
        # ---- Dashboard do Sub-diretor Pedagógico ----
        # (excluído explicitamente quem também for Diretor Geral — esse
        # é o "novo topo" da hierarquia e tem o seu próprio dashboard,
        # com a mesma aparência — ver _contexto_estatisticas_academicas
        # — mais abaixo; sem esta exclusão, o superuser real ficaria
        # sempre preso aqui, porque também passa em
        # eh_subdiretor_pedagogico.)

        context.update(_contexto_estatisticas_academicas(request))

        return render(
            request,
            'dashboards/admin.html',
            context
        )

    if usuario_do_grupo(user, 'Professor'):
        # ---- Dashboard do Professor ---- (lógica em _contexto_dashboard_professor)

        context.update(_contexto_dashboard_professor(request))

        return render(
            request,
            'dashboards/professor.html', context
        )

    if usuario_do_grupo(user, 'Aluno'):
        # ---- Dashboard do Aluno ---- (estatísticas vêm de
        # pautas/services/dashboard_aluno.estatisticas_aluno)

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
        # ---- Dashboard do Encarregado ---- (agrega estatísticas de cada
        # educando/dependente a partir de estatisticas_aluno)

        encarregado = getattr(user, 'encarregado', None)
        dependentes = (
            Aluno.objects.filter(encarregado=encarregado).select_related('turma').order_by('nome')
            if encarregado else Aluno.objects.none()
        )

        educandos = []
        total_em_risco = 0
        total_faltas_por_justificar = 0
        for dependente in dependentes:
            stats = estatisticas_aluno(dependente)
            em_risco = (
                (stats['media_geral'] is not None and stats['media_geral'] < MEDIA_MINIMA)
                or stats['frequencia'] < FREQUENCIA_MINIMA
            )
            faltas_por_justificar = Frequencia.pendentes_justificacao(aluno=dependente).count()

            if em_risco:
                total_em_risco += 1
            total_faltas_por_justificar += faltas_por_justificar

            educandos.append({
                'aluno': dependente,
                'media_geral': stats['media_geral'],
                'frequencia': stats['frequencia'],
                'em_risco': em_risco,
                'faltas_por_justificar': faltas_por_justificar,
                'mensagem_alerta': next(
                    (m for m in stats['mensagens'] if m['tipo'] == 'alerta'), None
                ),
            })

        context.update({
            'dependentes': dependentes,
            'educandos': educandos,
            'total_educandos': len(educandos),
            'total_em_risco': total_em_risco,
            'total_faltas_por_justificar': total_faltas_por_justificar,
            'grafico_educandos_labels': [e['aluno'].nome for e in educandos],
            'grafico_medias_dados': [
                float(e['media_geral']) if e['media_geral'] is not None else 0 for e in educandos
            ],
            'grafico_frequencia_dados': [e['frequencia'] for e in educandos],
        })

        return render(
            request,
            'dashboards/encarregado.html',
            context
        )

    if eh_diretor_geral(user):
        # ---- Dashboard do Diretor Geral do Complexo ---- (mesma
        # aparência/gráficos do Sub-diretor Pedagógico — a pedido
        # explícito do utilizador, 2026-08-11 — mais os cards próprios
        # do Diretor Geral: pendências agregadas das outras entidades e
        # as homologações/reclamações que só ele decide)

        context.update(_contexto_estatisticas_academicas(request))

        context.update({
            # Pendências agregadas das 3 entidades operacionais.
            'pedidos_documentos_pendentes': PedidoDocumento.objects.filter(
                status=PedidoDocumento.STATUS_PENDENTE
            ).count(),
            'pedidos_pagamento_pendentes': PedidoDocumento.objects.filter(
                status=PedidoDocumento.STATUS_PAGAMENTO_SUBMETIDO
            ).count(),
            'faltas_por_justificar_total': Frequencia.pendentes_justificacao().count(),
            # Homologações e reclamações — decisões que só o Diretor
            # Geral toma.
            'resultados_pendentes_homologacao': ResultadoDisciplina.objects.filter(
                status=ResultadoDisciplina.STATUS_VALIDADA, homologado_em__isnull=True
            ).count(),
            'reclamacoes_pendentes_diretor_geral': Reclamacao.objects.filter(
                encaminhado_para=Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL
            ).count(),
        })

        return render(
            request,
            'dashboards/diretor_geral.html',
            context
        )

    if eh_chefe_secretaria(user):
        # ---- Dashboard do Chefe de Secretaria ---- (Fase 1: a Secretaria
        # passa a ser o ponto único de entrada de pedidos de documentos e
        # pagamentos — responsabilidade que antes estava só no Sub-diretor
        # Pedagógico, ver dashboards/admin.html)

        pedidos_por_estado = {
            valor: PedidoDocumento.objects.filter(status=valor).count()
            for valor, _rotulo in PedidoDocumento.STATUS_CHOICES
        }
        rotulos_estado = dict(PedidoDocumento.STATUS_CHOICES)
        freq_dia_labels, freq_dia_dados = _frequencia_diaria(Frequencia.objects.all())

        context.update({
            'pedidos_documentos_pendentes': pedidos_por_estado.get(PedidoDocumento.STATUS_PENDENTE, 0),
            'pedidos_pagamento_pendentes': pedidos_por_estado.get(PedidoDocumento.STATUS_PAGAMENTO_SUBMETIDO, 0),
            'pedidos_prontos_levantamento': pedidos_por_estado.get(PedidoDocumento.STATUS_PRONTO, 0),
            'pedidos_estado_labels': [rotulos_estado[v] for v in pedidos_por_estado],
            'pedidos_estado_dados': list(pedidos_por_estado.values()),
            'freq_diaria_labels': freq_dia_labels,
            'freq_diaria_dados': freq_dia_dados,
        })

        return render(
            request,
            'dashboards/chefe_secretaria.html',
            context
        )

    if eh_coordenador_turno(user):
        # ---- Dashboard do Coordenador de Turno ---- (Fase 2: turmas do seu
        # turno, escopadas por Turma.periodo — não é preciso nenhum campo
        # novo, "turno" já existia no modelo com esse nome)

        turno = getattr(user.perfil, 'turno_coordenado', '') if hasattr(user, 'perfil') else ''
        turmas_turno = (
            Turma.objects.filter(periodo=turno, ativo=True).select_related('classe')
            if turno else Turma.objects.none()
        )
        turmas_ids = list(turmas_turno.values_list('id', flat=True))

        diretores_turma_turno = DiretorTurma.objects.filter(
            turma_id__in=turmas_ids, ativo=True
        ).select_related('professor__user', 'turma__classe')

        faltas_por_justificar_turno = Frequencia.pendentes_justificacao(
            aluno__turma_id__in=turmas_ids
        ).count()

        total_professores_turno = AtribuicaoDocente.objects.filter(
            turma_id__in=turmas_ids, ativo=True
        ).values('professor_id').distinct().count()

        avaliacoes_por_estado = {
            valor: Avaliacao.objects.filter(atribuicao__turma_id__in=turmas_ids, status=valor).count()
            for valor, _rotulo in Avaliacao.STATUS_CHOICES
        }
        rotulos_avaliacao = dict(Avaliacao.STATUS_CHOICES)

        # Turmas do turno com frequência abaixo de 85% — alerta de
        # assiduidade crónica.
        frequencias_turno = list(
            Frequencia.objects.filter(aluno__turma_id__in=turmas_ids).select_related('aluno__turma')
        )
        totais_por_turma = {}
        presentes_por_turma = {}
        for f in frequencias_turno:
            chave = str(f.aluno.turma)
            totais_por_turma[chave] = totais_por_turma.get(chave, 0) + 1
            if f.estado in (Frequencia.PRESENTE, Frequencia.ATRASO):
                presentes_por_turma[chave] = presentes_por_turma.get(chave, 0) + 1
        turmas_frequencia_baixa = sorted(
            (
                {'turma': turma, 'percentagem': round(presentes_por_turma.get(turma, 0) / total * 100, 1)}
                for turma, total in totais_por_turma.items()
                if total and round(presentes_por_turma.get(turma, 0) / total * 100, 1) < 85
            ),
            key=lambda item: item['percentagem'],
        )

        freq_dia_labels, freq_dia_dados = _frequencia_diaria(frequencias_turno)

        context.update({
            'turno_coordenado_display': dict(Turma.PERIODO_CHOICES).get(turno, '—'),
            'turmas_turno': turmas_turno,
            'total_alunos_turno': Aluno.objects.filter(
                turma_id__in=turmas_ids, estado=Aluno.ESTADO_ATIVO
            ).count(),
            'total_professores_turno': total_professores_turno,
            'diretores_turma_turno': diretores_turma_turno,
            'faltas_por_justificar_turno': faltas_por_justificar_turno,
            'avaliacoes_estado_labels': [rotulos_avaliacao[v] for v in avaliacoes_por_estado],
            'avaliacoes_estado_dados': list(avaliacoes_por_estado.values()),
            'turmas_frequencia_baixa': turmas_frequencia_baixa,
            'freq_diaria_labels': freq_dia_labels,
            'freq_diaria_dados': freq_dia_dados,
        })

        return render(
            request,
            'dashboards/coordenador_turno.html',
            context
        )

    if eh_coordenador_pais_encarregados(user):
        # ---- Dashboard do Coordenador de Pais e Encarregados de Educação ----
        # (Fase 2: alunos em risco com contacto do encarregado, faltas por
        # justificar por turma, reclamações em aberto)

        ano_letivo_atual = AnoLetivo.objects.filter(ativo=True).first() or AnoLetivo.objects.first()

        resultados = (
            ResultadoDisciplina.objects.filter(
                ano_letivo=ano_letivo_atual, status=ResultadoDisciplina.STATUS_VALIDADA
            ).select_related('aluno', 'aluno__turma', 'aluno__encarregado__user')
            if ano_letivo_atual else ResultadoDisciplina.objects.none()
        )

        medias_por_aluno = {}
        for resultado in resultados:
            if resultado.mf:
                medias_por_aluno.setdefault(resultado.aluno, []).append(float(resultado.mf))

        alunos_risco_media = sorted(
            (
                {'aluno': aluno, 'encarregado': aluno.encarregado, 'media': _media(valores)}
                for aluno, valores in medias_por_aluno.items()
                if _media(valores) is not None and _media(valores) < 10
            ),
            key=lambda item: item['media'],
        )

        faltas_por_turma = {}
        faltas_sem_justificacao = Frequencia.pendentes_justificacao().select_related('aluno__turma')
        for falta in faltas_sem_justificacao:
            chave = str(falta.aluno.turma)
            faltas_por_turma[chave] = faltas_por_turma.get(chave, 0) + 1

        reclamacoes_por_estado = {
            valor: Reclamacao.objects.filter(estado=valor).count()
            for valor, _rotulo in Reclamacao.ESTADO_CHOICES
        }
        rotulos_reclamacao = dict(Reclamacao.ESTADO_CHOICES)

        context.update({
            'alunos_risco_media': alunos_risco_media[:20],
            'total_alunos_risco': len(alunos_risco_media),
            'faltas_por_turma': [
                {'turma': turma, 'total': total} for turma, total in faltas_por_turma.items()
            ],
            'faltas_turma_labels': list(faltas_por_turma.keys()),
            'faltas_turma_dados': list(faltas_por_turma.values()),
            'reclamacoes_abertas': reclamacoes_por_estado.get(Reclamacao.ESTADO_ABERTA, 0),
            'reclamacoes_estado_labels': [rotulos_reclamacao[v] for v in reclamacoes_por_estado],
            'reclamacoes_estado_dados': list(reclamacoes_por_estado.values()),
        })

        return render(
            request,
            'dashboards/coordenador_pais.html',
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


def _subdiretores_pedagogicos_qs():
    return User.objects.filter(
        Q(groups__name='Sub-diretor Pedagógico') | Q(is_superuser=True)
    ).distinct()


class SubdiretorPedagogicoListView(SuperuserRequeridoMixin, ListView):
    model = User
    template_name = 'accounts/subdiretor_pedagogico_lista.html'
    context_object_name = 'subdiretores_pedagogicos'

    def get_queryset(self):
        return _subdiretores_pedagogicos_qs().order_by('username')


class SubdiretorPedagogicoCreateView(SuperuserRequeridoMixin, View):
    template_name = 'accounts/subdiretor_pedagogico_cadastro.html'

    def get(self, request):
        form = SubdiretorPedagogicoCadastroForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = SubdiretorPedagogicoCadastroForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
            )
            grupo_subdiretor_pedagogico, _ = Group.objects.get_or_create(name='Sub-diretor Pedagógico')
            user.groups.add(grupo_subdiretor_pedagogico)
            messages.success(request, 'Sub-diretor Pedagógico cadastrado com sucesso.')
            return redirect('subdiretor_pedagogico_lista')
        return render(request, self.template_name, {'form': form})


class SubdiretorPedagogicoDetailView(SuperuserRequeridoMixin, DetailView):
    template_name = 'accounts/subdiretor_pedagogico_detalhe.html'
    context_object_name = 'subdiretor_pedagogico'

    def get_queryset(self):
        return _subdiretores_pedagogicos_qs()


class SubdiretorPedagogicoUpdateView(SuperuserRequeridoMixin, View):
    template_name = 'accounts/subdiretor_pedagogico_editar.html'

    def get(self, request, pk):
        subdiretor_pedagogico = get_object_or_404(_subdiretores_pedagogicos_qs(), pk=pk)
        form = SubdiretorPedagogicoEdicaoForm(initial={
            'first_name': subdiretor_pedagogico.first_name,
            'last_name': subdiretor_pedagogico.last_name,
            'email': subdiretor_pedagogico.email,
            'ativo': subdiretor_pedagogico.is_active,
        })
        return render(request, self.template_name, {'form': form, 'subdiretor_pedagogico': subdiretor_pedagogico})

    def post(self, request, pk):
        subdiretor_pedagogico = get_object_or_404(_subdiretores_pedagogicos_qs(), pk=pk)
        form = SubdiretorPedagogicoEdicaoForm(request.POST)
        if form.is_valid():
            subdiretor_pedagogico.first_name = form.cleaned_data['first_name']
            subdiretor_pedagogico.last_name = form.cleaned_data['last_name']
            subdiretor_pedagogico.email = form.cleaned_data['email']
            subdiretor_pedagogico.is_active = form.cleaned_data['ativo']
            subdiretor_pedagogico.save()
            messages.success(request, 'Sub-diretor Pedagógico atualizado com sucesso.')
            return redirect('subdiretor_pedagogico_lista')
        return render(request, self.template_name, {'form': form, 'subdiretor_pedagogico': subdiretor_pedagogico})


class SubdiretorPedagogicoDeleteView(SuperuserRequeridoMixin, DeleteView):
    template_name = 'accounts/subdiretor_pedagogico_excluir.html'
    context_object_name = 'subdiretor_pedagogico'
    success_url = reverse_lazy('subdiretor_pedagogico_lista')

    def get_queryset(self):
        return _subdiretores_pedagogicos_qs()

    def post(self, request, *args, **kwargs):
        if self.get_object() == request.user:
            messages.error(request, 'Não é possível eliminar a sua própria conta.')
            return redirect('subdiretor_pedagogico_lista')
        return super().post(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# CRUD genérico de "contas administrativas puras" (sem modelo de domínio
# próprio, tal como Sub-diretor Pedagógico) — reaproveitado pelos 4 novos
# papéis administrativos do Complexo Escolar. Cada subclasse só define o
# grupo Django e os textos/urls; a lógica fica centralizada aqui.
# ---------------------------------------------------------------------------

GRUPO_DIRETOR_GERAL = 'Diretor Geral do Complexo'
GRUPO_CHEFE_SECRETARIA = 'Chefe de Secretaria'
GRUPO_COORDENADOR_TURNO = 'Coordenador de Turno'
GRUPO_COORDENADOR_PAIS = 'Coordenador de Pais e Encarregados de Educação'


def _contas_por_grupo_qs(grupo_nome, incluir_superuser=False):
    if incluir_superuser:
        return User.objects.filter(Q(groups__name=grupo_nome) | Q(is_superuser=True)).distinct()
    return User.objects.filter(groups__name=grupo_nome).distinct()


class ContaAdministrativaListView(SuperuserRequeridoMixin, ListView):
    model = User
    grupo_nome = None
    incluir_superuser = False
    template_name = 'accounts/conta_admin_lista.html'
    context_object_name = 'contas'
    titulo_singular = ''
    titulo_plural = ''
    url_novo_name = ''
    url_detalhe_name = ''
    url_editar_name = ''
    url_excluir_name = ''

    def get_queryset(self):
        return _contas_por_grupo_qs(self.grupo_nome, self.incluir_superuser).order_by('username')

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update({
            'titulo_singular': self.titulo_singular,
            'titulo_plural': self.titulo_plural,
            'url_novo_name': self.url_novo_name,
            'url_detalhe_name': self.url_detalhe_name,
            'url_editar_name': self.url_editar_name,
            'url_excluir_name': self.url_excluir_name,
        })
        return contexto


class ContaAdministrativaCreateView(SuperuserRequeridoMixin, View):
    grupo_nome = None
    template_name = 'accounts/conta_admin_cadastro.html'
    titulo_singular = ''
    url_lista_name = ''
    form_class = ContaAdministrativaCadastroForm

    def _contexto(self, form):
        return {
            'form': form,
            'titulo_singular': self.titulo_singular,
            'url_lista_name': self.url_lista_name,
        }

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, self._contexto(form))

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
            )
            grupo, _ = Group.objects.get_or_create(name=self.grupo_nome)
            user.groups.add(grupo)
            self._pos_criar(user, form)
            messages.success(request, f'{self.titulo_singular} cadastrado(a) com sucesso.')
            return redirect(self.url_lista_name)
        return render(request, self.template_name, self._contexto(form))

    def _pos_criar(self, user, form):
        """Hook para subclasses gravarem campos extra (fora do form
        genérico de conta) depois de o User/Group já estarem criados."""


class ContaAdministrativaDetailView(SuperuserRequeridoMixin, DetailView):
    grupo_nome = None
    incluir_superuser = False
    template_name = 'accounts/conta_admin_detalhe.html'
    context_object_name = 'conta'
    titulo_singular = ''
    url_lista_name = ''
    url_editar_name = ''

    def get_queryset(self):
        return _contas_por_grupo_qs(self.grupo_nome, self.incluir_superuser)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update({
            'titulo_singular': self.titulo_singular,
            'url_lista_name': self.url_lista_name,
            'url_editar_name': self.url_editar_name,
        })
        return contexto


class ContaAdministrativaUpdateView(SuperuserRequeridoMixin, View):
    grupo_nome = None
    incluir_superuser = False
    template_name = 'accounts/conta_admin_editar.html'
    titulo_singular = ''
    url_lista_name = ''
    form_class = ContaAdministrativaEdicaoForm

    def get_queryset(self):
        return _contas_por_grupo_qs(self.grupo_nome, self.incluir_superuser)

    def _initial(self, conta):
        return {
            'first_name': conta.first_name,
            'last_name': conta.last_name,
            'email': conta.email,
            'ativo': conta.is_active,
        }

    def _contexto(self, form, conta):
        return {
            'form': form,
            'conta': conta,
            'titulo_singular': self.titulo_singular,
            'url_lista_name': self.url_lista_name,
        }

    def get(self, request, pk):
        conta = get_object_or_404(self.get_queryset(), pk=pk)
        form = self.form_class(initial=self._initial(conta))
        return render(request, self.template_name, self._contexto(form, conta))

    def post(self, request, pk):
        conta = get_object_or_404(self.get_queryset(), pk=pk)
        form = self.form_class(request.POST)
        if form.is_valid():
            conta.first_name = form.cleaned_data['first_name']
            conta.last_name = form.cleaned_data['last_name']
            conta.email = form.cleaned_data['email']
            conta.is_active = form.cleaned_data['ativo']
            conta.save()
            self._pos_editar(conta, form)
            messages.success(request, f'{self.titulo_singular} atualizado(a) com sucesso.')
            return redirect(self.url_lista_name)
        return render(request, self.template_name, self._contexto(form, conta))

    def _pos_editar(self, conta, form):
        """Hook para subclasses gravarem campos extra (fora do form
        genérico de conta) depois dos dados base já terem sido guardados."""


class ContaAdministrativaDeleteView(SuperuserRequeridoMixin, DeleteView):
    grupo_nome = None
    incluir_superuser = False
    template_name = 'accounts/conta_admin_excluir.html'
    context_object_name = 'conta'
    titulo_singular = ''
    url_lista_name = ''

    def get_queryset(self):
        return _contas_por_grupo_qs(self.grupo_nome, self.incluir_superuser)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['titulo_singular'] = self.titulo_singular
        contexto['url_lista_name'] = self.url_lista_name
        return contexto

    def get_success_url(self):
        return reverse_lazy(self.url_lista_name)

    def post(self, request, *args, **kwargs):
        if self.get_object() == request.user:
            messages.error(request, 'Não é possível eliminar a sua própria conta.')
            return redirect(self.url_lista_name)
        return super().post(request, *args, **kwargs)


class DiretorGeralListView(ContaAdministrativaListView):
    grupo_nome = GRUPO_DIRETOR_GERAL
    incluir_superuser = True
    titulo_singular = 'Diretor Geral'
    titulo_plural = 'Diretores Gerais'
    url_novo_name = 'diretor_geral_novo'
    url_detalhe_name = 'diretor_geral_detalhe'
    url_editar_name = 'diretor_geral_editar'
    url_excluir_name = 'diretor_geral_excluir'


class DiretorGeralCreateView(ContaAdministrativaCreateView):
    grupo_nome = GRUPO_DIRETOR_GERAL
    titulo_singular = 'Diretor Geral'
    url_lista_name = 'diretor_geral_lista'


class DiretorGeralDetailView(ContaAdministrativaDetailView):
    grupo_nome = GRUPO_DIRETOR_GERAL
    incluir_superuser = True
    titulo_singular = 'Diretor Geral'
    url_lista_name = 'diretor_geral_lista'
    url_editar_name = 'diretor_geral_editar'


class DiretorGeralUpdateView(ContaAdministrativaUpdateView):
    grupo_nome = GRUPO_DIRETOR_GERAL
    incluir_superuser = True
    titulo_singular = 'Diretor Geral'
    url_lista_name = 'diretor_geral_lista'


class DiretorGeralDeleteView(ContaAdministrativaDeleteView):
    grupo_nome = GRUPO_DIRETOR_GERAL
    incluir_superuser = True
    titulo_singular = 'Diretor Geral'
    url_lista_name = 'diretor_geral_lista'


class ChefeSecretariaListView(ContaAdministrativaListView):
    grupo_nome = GRUPO_CHEFE_SECRETARIA
    titulo_singular = 'Chefe de Secretaria'
    titulo_plural = 'Chefes de Secretaria'
    url_novo_name = 'chefe_secretaria_novo'
    url_detalhe_name = 'chefe_secretaria_detalhe'
    url_editar_name = 'chefe_secretaria_editar'
    url_excluir_name = 'chefe_secretaria_excluir'


class ChefeSecretariaCreateView(ContaAdministrativaCreateView):
    grupo_nome = GRUPO_CHEFE_SECRETARIA
    titulo_singular = 'Chefe de Secretaria'
    url_lista_name = 'chefe_secretaria_lista'


class ChefeSecretariaDetailView(ContaAdministrativaDetailView):
    grupo_nome = GRUPO_CHEFE_SECRETARIA
    titulo_singular = 'Chefe de Secretaria'
    url_lista_name = 'chefe_secretaria_lista'
    url_editar_name = 'chefe_secretaria_editar'


class ChefeSecretariaUpdateView(ContaAdministrativaUpdateView):
    grupo_nome = GRUPO_CHEFE_SECRETARIA
    titulo_singular = 'Chefe de Secretaria'
    url_lista_name = 'chefe_secretaria_lista'


class ChefeSecretariaDeleteView(ContaAdministrativaDeleteView):
    grupo_nome = GRUPO_CHEFE_SECRETARIA
    titulo_singular = 'Chefe de Secretaria'
    url_lista_name = 'chefe_secretaria_lista'


class CoordenadorTurnoListView(ContaAdministrativaListView):
    grupo_nome = GRUPO_COORDENADOR_TURNO
    titulo_singular = 'Coordenador de Turno'
    titulo_plural = 'Coordenadores de Turno'
    url_novo_name = 'coordenador_turno_novo'
    url_detalhe_name = 'coordenador_turno_detalhe'
    url_editar_name = 'coordenador_turno_editar'
    url_excluir_name = 'coordenador_turno_excluir'


class CoordenadorTurnoCreateView(ContaAdministrativaCreateView):
    grupo_nome = GRUPO_COORDENADOR_TURNO
    titulo_singular = 'Coordenador de Turno'
    url_lista_name = 'coordenador_turno_lista'
    form_class = CoordenadorTurnoCadastroForm

    def _pos_criar(self, user, form):
        user.perfil.turno_coordenado = form.cleaned_data['turno_coordenado']
        user.perfil.save()


class CoordenadorTurnoDetailView(ContaAdministrativaDetailView):
    grupo_nome = GRUPO_COORDENADOR_TURNO
    titulo_singular = 'Coordenador de Turno'
    url_lista_name = 'coordenador_turno_lista'
    url_editar_name = 'coordenador_turno_editar'


class CoordenadorTurnoUpdateView(ContaAdministrativaUpdateView):
    grupo_nome = GRUPO_COORDENADOR_TURNO
    titulo_singular = 'Coordenador de Turno'
    url_lista_name = 'coordenador_turno_lista'
    form_class = CoordenadorTurnoEdicaoForm

    def _initial(self, conta):
        initial = super()._initial(conta)
        initial['turno_coordenado'] = getattr(conta.perfil, 'turno_coordenado', '')
        return initial

    def _pos_editar(self, conta, form):
        conta.perfil.turno_coordenado = form.cleaned_data['turno_coordenado']
        conta.perfil.save()


class CoordenadorTurnoDeleteView(ContaAdministrativaDeleteView):
    grupo_nome = GRUPO_COORDENADOR_TURNO
    titulo_singular = 'Coordenador de Turno'
    url_lista_name = 'coordenador_turno_lista'


class CoordenadorPaisListView(ContaAdministrativaListView):
    grupo_nome = GRUPO_COORDENADOR_PAIS
    titulo_singular = 'Coordenador de Pais e Encarregados de Educação'
    titulo_plural = 'Coordenadores de Pais e Encarregados de Educação'
    url_novo_name = 'coordenador_pais_novo'
    url_detalhe_name = 'coordenador_pais_detalhe'
    url_editar_name = 'coordenador_pais_editar'
    url_excluir_name = 'coordenador_pais_excluir'


class CoordenadorPaisCreateView(ContaAdministrativaCreateView):
    grupo_nome = GRUPO_COORDENADOR_PAIS
    titulo_singular = 'Coordenador de Pais e Encarregados de Educação'
    url_lista_name = 'coordenador_pais_lista'


class CoordenadorPaisDetailView(ContaAdministrativaDetailView):
    grupo_nome = GRUPO_COORDENADOR_PAIS
    titulo_singular = 'Coordenador de Pais e Encarregados de Educação'
    url_lista_name = 'coordenador_pais_lista'
    url_editar_name = 'coordenador_pais_editar'


class CoordenadorPaisUpdateView(ContaAdministrativaUpdateView):
    grupo_nome = GRUPO_COORDENADOR_PAIS
    titulo_singular = 'Coordenador de Pais e Encarregados de Educação'
    url_lista_name = 'coordenador_pais_lista'


class CoordenadorPaisDeleteView(ContaAdministrativaDeleteView):
    grupo_nome = GRUPO_COORDENADOR_PAIS
    titulo_singular = 'Coordenador de Pais e Encarregados de Educação'
    url_lista_name = 'coordenador_pais_lista'
