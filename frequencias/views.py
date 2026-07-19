import mimetypes
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (ListView, CreateView,
    UpdateView, DeleteView)

from accounts.decoracors import admin_ou_professor_requerido
from accounts.mixins import AdminOuProfessorRequeridoMixin
from accounts.utils import eh_administrador, eh_professor, eh_aluno, eh_encarregado
from alunos.models import Aluno
from professores.models import AtribuicaoDocente
from turmas.models import HorarioAula, Turma
from .models import Frequencia, JustificacaoFalta
from .forms import FrequenciaForm, JustificacaoFaltaForm, RegistoFrequenciaFormSet

DIA_SEMANA_POR_WEEKDAY = {
    0: HorarioAula.SEGUNDA,
    1: HorarioAula.TERCA,
    2: HorarioAula.QUARTA,
    3: HorarioAula.QUINTA,
    4: HorarioAula.SEXTA,
}


class FrequenciaListView(LoginRequiredMixin, ListView):
    model = Frequencia
    template_name = 'frequencias/lista.html'
    context_object_name = 'frequencias'
    paginate_by = 20

    def get_ordenacao(self):
        ordenacao = self.request.GET.get('ordenar')
        return ordenacao if ordenacao in ('data', '-data') else '-data'

    def get_queryset(self):
        user = self.request.user
        queryset = Frequencia.objects.select_related(
            'aluno', 'atribuicao__professor__user',
            'atribuicao__disciplina', 'atribuicao__turma', 'justificacaofalta'
        )

        if eh_administrador(user):
            pass
        elif eh_professor(user):
            queryset = queryset.filter(atribuicao__professor__user=user)
        elif eh_aluno(user):
            aluno = getattr(user, 'aluno', None)
            queryset = queryset.filter(aluno=aluno) if aluno else queryset.none()
        elif eh_encarregado(user):
            encarregado = getattr(user, 'encarregado', None)
            queryset = queryset.filter(aluno__encarregado=encarregado) if encarregado else queryset.none()
        else:
            queryset = queryset.none()

        data = self.request.GET.get('data')
        if data:
            queryset = queryset.filter(data=data)

        turma_id = self.request.GET.get('turma')
        if turma_id:
            queryset = queryset.filter(atribuicao__turma_id=turma_id)

        mes_str = self.request.GET.get('mes')
        if mes_str:
            try:
                ano, mes = (int(parte) for parte in mes_str.split('-'))
                queryset = queryset.filter(data__year=ano, data__month=mes)
            except ValueError:
                pass

        return queryset.order_by(self.get_ordenacao())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['data_filtro'] = self.request.GET.get('data', '')
        context['ordenacao'] = self.get_ordenacao()
        context['pode_gerir'] = (
            eh_administrador(self.request.user) or eh_professor(self.request.user)
        )
        context['pode_justificar'] = (
            eh_aluno(self.request.user) or eh_encarregado(self.request.user)
        )
        context['mes'] = self.request.GET.get('mes', '')
        turma_id = self.request.GET.get('turma')
        context['turma_id'] = turma_id
        context['turma_selecionada'] = (
            Turma.objects.filter(pk=turma_id).first() if turma_id else None
        )
        return context


@login_required
def frequencia_lista_view(request):
    user = request.user
    pode_gerir = eh_administrador(user) or eh_professor(user)

    if not pode_gerir or request.GET.get('turma'):
        return FrequenciaListView.as_view()(request)

    return _resumo_frequencia_por_turma(request)


def _resumo_frequencia_por_turma(request):
    user = request.user
    atribuicoes = AtribuicaoDocente.objects.filter(ativo=True).select_related('turma', 'disciplina')
    if not eh_administrador(user):
        atribuicoes = atribuicoes.filter(professor__user=user)

    turmas = (
        Turma.objects
        .filter(pk__in=atribuicoes.values_list('turma_id', flat=True))
        .distinct()
        .order_by('classe__nome', 'nome')
    )

    hoje = timezone.localdate()
    mes_str = request.GET.get('mes') or hoje.strftime('%Y-%m')
    try:
        ano, mes = (int(parte) for parte in mes_str.split('-'))
    except ValueError:
        ano, mes = hoje.year, hoje.month
        mes_str = hoje.strftime('%Y-%m')

    frequencias = Frequencia.objects.filter(
        atribuicao__in=atribuicoes, data__year=ano, data__month=mes,
    ).select_related('atribuicao__turma')

    dados_por_turma = {
        turma.id: {
            'turma': turma,
            'total_alunos': turma.contar_alunos(),
            'dias': set(),
            'presentes': 0,
            'faltas_injustificadas': 0,
            'faltas_justificadas': 0,
        }
        for turma in turmas
    }

    for f in frequencias:
        registo = dados_por_turma.get(f.atribuicao.turma_id)
        if registo is None:
            continue
        registo['dias'].add(f.data)
        if f.estado in (Frequencia.PRESENTE, Frequencia.ATRASO):
            registo['presentes'] += 1
        elif f.estado == Frequencia.FALTA:
            registo['faltas_injustificadas'] += 1
        elif f.estado == Frequencia.JUSTIFICADA:
            registo['faltas_justificadas'] += 1

    linhas = []
    for dados in dados_por_turma.values():
        total_faltas = dados['faltas_injustificadas'] + dados['faltas_justificadas']
        total_registos = dados['presentes'] + total_faltas
        taxa = round(dados['presentes'] / total_registos * 100, 1) if total_registos else None
        linhas.append({
            'turma': dados['turma'],
            'total_alunos': dados['total_alunos'],
            'aulas_dadas': len(dados['dias']),
            'faltas_justificadas': dados['faltas_justificadas'],
            'faltas_injustificadas': dados['faltas_injustificadas'],
            'total_faltas': total_faltas,
            'taxa_assiduidade': taxa,
        })
    linhas.sort(key=lambda item: str(item['turma']))

    total_alunos = sum(l['total_alunos'] for l in linhas)
    total_faltas_justificadas = sum(l['faltas_justificadas'] for l in linhas)
    total_faltas_injustificadas = sum(l['faltas_injustificadas'] for l in linhas)
    total_faltas = total_faltas_justificadas + total_faltas_injustificadas
    total_presentes = sum(dados['presentes'] for dados in dados_por_turma.values())
    total_registos = total_presentes + total_faltas
    taxa_geral = round(total_presentes / total_registos * 100, 1) if total_registos else None

    linhas_com_taxa = [l for l in linhas if l['taxa_assiduidade'] is not None]
    turma_critica = min(linhas_com_taxa, key=lambda l: l['taxa_assiduidade']) if linhas_com_taxa else None
    melhor_turma = max(linhas_com_taxa, key=lambda l: l['taxa_assiduidade']) if linhas_com_taxa else None

    contexto = {
        'modo_resumo': True,
        'mes': mes_str,
        'linhas_resumo': linhas,
        'total_alunos': total_alunos,
        'total_faltas_justificadas': total_faltas_justificadas,
        'total_faltas_injustificadas': total_faltas_injustificadas,
        'total_faltas': total_faltas,
        'taxa_geral': taxa_geral,
        'turma_critica': turma_critica,
        'melhor_turma': melhor_turma,
        'pode_gerir': True,
    }
    return render(request, 'frequencias/resumo_turmas.html', contexto)


class FrequenciaCreateView(AdminOuProfessorRequeridoMixin, CreateView):
    model = Frequencia
    form_class = FrequenciaForm
    template_name = 'frequencias/form.html'
    success_url = reverse_lazy('frequencia_lista')

    def get_initial(self):
        initial = super().get_initial()
        atribuicao_id = self.request.GET.get('atribuicao')
        if atribuicao_id:
            initial['atribuicao'] = atribuicao_id
        initial.setdefault('data', timezone.localdate())
        return initial


class FrequenciaUpdateView(AdminOuProfessorRequeridoMixin, UpdateView):
    model = Frequencia
    form_class = FrequenciaForm
    template_name = 'frequencias/form.html'
    success_url = reverse_lazy('frequencia_lista')

    def get_queryset(self):
        queryset = super().get_queryset()
        if eh_administrador(self.request.user):
            return queryset
        return queryset.filter(atribuicao__professor__user=self.request.user)


class FrequenciaDeleteView(AdminOuProfessorRequeridoMixin, DeleteView):
    model = Frequencia
    template_name = 'frequencias/excluir.html'
    success_url = reverse_lazy('frequencia_lista')

    def get_queryset(self):
        queryset = super().get_queryset()
        if eh_administrador(self.request.user):
            return queryset
        return queryset.filter(atribuicao__professor__user=self.request.user)


@admin_ou_professor_requerido
def lancamento_frequencia(request):
    atribuicoes = AtribuicaoDocente.objects.filter(ativo=True).select_related(
        'disciplina', 'turma', 'ano_letivo'
    ).prefetch_related('horarios')
    if not eh_administrador(request.user):
        atribuicoes = atribuicoes.filter(professor__user=request.user)
    atribuicoes = atribuicoes.order_by('turma__classe__nome', 'turma__nome', 'disciplina__nome')

    contexto = {'atribuicoes': atribuicoes, 'atribuicao': None, 'data': None, 'mostrar_formulario': False}

    if not atribuicoes.exists():
        messages.warning(request, 'Não existe nenhuma atribuição docente ativa associada a si.')
        return render(request, 'frequencias/lancamento.html', contexto)

    dia_display_map = dict(HorarioAula.DIA_SEMANA_CHOICES)
    ordem_dias = list(DIA_SEMANA_POR_WEEKDAY.values())

    turmas_disponiveis = Turma.objects.filter(
        pk__in=atribuicoes.values_list('turma_id', flat=True)
    ).order_by('classe__nome', 'nome')
    contexto['turmas_disponiveis'] = turmas_disponiveis

    atribuicao_id_post = request.POST.get('atribuicao')
    if atribuicao_id_post:
        atribuicao = atribuicoes.filter(pk=atribuicao_id_post).first()
        turma_selecionada = atribuicao.turma if atribuicao else None
    else:
        turma_id = request.GET.get('turma')
        turma_selecionada = (
            turmas_disponiveis.filter(pk=turma_id).first() if turma_id else turmas_disponiveis.first()
        )
        atribuicao = None

    contexto['turma_selecionada'] = turma_selecionada

    atribuicoes_da_turma = (
        atribuicoes.filter(turma=turma_selecionada) if turma_selecionada else atribuicoes.none()
    )
    contexto['atribuicoes_da_turma'] = atribuicoes_da_turma

    if atribuicao is None and turma_selecionada is not None:
        disciplina_id = request.GET.get('disciplina')
        if disciplina_id:
            atribuicao = atribuicoes_da_turma.filter(disciplina_id=disciplina_id).first()
        if atribuicao is None:
            atribuicao = atribuicoes_da_turma.first()

    contexto['atribuicao'] = atribuicao

    if atribuicao is None:
        messages.info(request, 'Escolha uma turma e uma disciplina para lançar a frequência.')
        return render(request, 'frequencias/lancamento.html', contexto)

    dias_codigos = {h.dia_semana for h in atribuicao.horarios.all()}
    dias_ordenados = [dia_display_map[codigo] for codigo in ordem_dias if codigo in dias_codigos]
    dia_aula_display = ', '.join(dias_ordenados) or 'Sem horário definido'
    contexto['dia_aula_display'] = dia_aula_display

    data_str = request.GET.get('data') or request.POST.get('data')
    try:
        data_selecionada = date.fromisoformat(data_str) if data_str else timezone.localdate()
    except ValueError:
        data_selecionada = timezone.localdate()
    contexto['data'] = data_selecionada

    dia_semana_data = DIA_SEMANA_POR_WEEKDAY.get(data_selecionada.weekday())
    if dia_semana_data not in dias_codigos:
        if request.method == 'POST':
            messages.error(
                request,
                f'{atribuicao.disciplina} não tem aula nesta data — o dia de aula é {dia_aula_display}. '
                'Lançamento bloqueado.'
            )
        else:
            messages.info(
                request,
                f'{atribuicao.disciplina} ({atribuicao.turma}) tem aula à(s) {dia_aula_display}. '
                'Ajuste a data para lançar a frequência.'
            )
        return render(request, 'frequencias/lancamento.html', contexto)

    pode_editar = eh_administrador(request.user) or atribuicao.professor.user_id == request.user.id

    alunos = list(
        Aluno.objects.filter(turma=atribuicao.turma, estado=Aluno.ESTADO_ATIVO).order_by('nome')
    )

    if request.method == 'POST':
        if not pode_editar:
            return render(request, 'dashboards/sem_permissao.html', status=403)

        formset = RegistoFrequenciaFormSet(request.POST)
        if formset.is_valid():
            gravados = 0
            for form in formset:
                aluno_id = form.cleaned_data['aluno_id']
                estado = form.cleaned_data['estado']
                Frequencia.objects.update_or_create(
                    aluno_id=aluno_id, atribuicao=atribuicao, data=data_selecionada,
                    defaults={'estado': estado},
                )
                gravados += 1

            if gravados:
                messages.success(request, f'Frequência registada para {gravados} aluno(s).')

            return redirect(
                f"{reverse('lancamento_frequencia')}?turma={atribuicao.turma_id}"
                f"&disciplina={atribuicao.disciplina_id}&data={data_selecionada.isoformat()}"
            )
    else:
        frequencias_existentes = {
            frequencia.aluno_id: frequencia
            for frequencia in Frequencia.objects.filter(
                atribuicao=atribuicao, data=data_selecionada, aluno__in=alunos
            )
        }
        initial = [
            {
                'aluno_id': aluno.id,
                'estado': frequencias_existentes[aluno.id].estado
                if aluno.id in frequencias_existentes
                else Frequencia.PRESENTE,
            }
            for aluno in alunos
        ]
        formset = RegistoFrequenciaFormSet(initial=initial)

    linhas = list(zip(alunos, formset))

    contexto.update({
        'formset': formset,
        'linhas': linhas,
        'pode_editar': pode_editar,
        'mostrar_formulario': True,
    })
    return render(request, 'frequencias/lancamento.html', contexto)


@admin_ou_professor_requerido
def relatorio_assiduidade(request):
    atribuicoes = AtribuicaoDocente.objects.filter(ativo=True).select_related(
        'disciplina', 'turma', 'ano_letivo'
    )
    if not eh_administrador(request.user):
        atribuicoes = atribuicoes.filter(professor__user=request.user)
    atribuicoes = atribuicoes.order_by('turma__classe__nome', 'turma__nome', 'disciplina__nome')

    turmas = (
        Turma.objects
        .filter(atribuicaodocente__in=atribuicoes)
        .distinct()
        .order_by('classe__nome', 'nome')
    )

    hoje = timezone.localdate()
    mes_str = request.GET.get('mes') or hoje.strftime('%Y-%m')
    try:
        ano, mes = (int(parte) for parte in mes_str.split('-'))
    except ValueError:
        ano, mes = hoje.year, hoje.month
        mes_str = hoje.strftime('%Y-%m')

    turma_id = request.GET.get('turma')

    frequencias = Frequencia.objects.filter(
        atribuicao__in=atribuicoes, data__year=ano, data__month=mes,
    ).select_related('aluno', 'aluno__turma', 'atribuicao__turma')

    if turma_id:
        frequencias = frequencias.filter(atribuicao__turma_id=turma_id)

    presencas = 0
    faltas = 0
    justificadas = 0
    por_turma = {}
    por_aluno = {}

    for f in frequencias:
        turma_registo = por_turma.setdefault(
            f.atribuicao.turma, {'presentes': 0, 'ausentes': 0, 'justificadas': 0}
        )
        if f.estado in (Frequencia.PRESENTE, Frequencia.ATRASO):
            presencas += 1
            turma_registo['presentes'] += 1
        elif f.estado == Frequencia.FALTA:
            faltas += 1
            turma_registo['ausentes'] += 1
            registo_aluno = por_aluno.setdefault(f.aluno, 0)
            por_aluno[f.aluno] = registo_aluno + 1
        elif f.estado == Frequencia.JUSTIFICADA:
            justificadas += 1
            turma_registo['justificadas'] += 1
            registo_aluno = por_aluno.setdefault(f.aluno, 0)
            por_aluno[f.aluno] = registo_aluno + 1

    total = presencas + faltas + justificadas
    taxa_absentismo = round((faltas + justificadas) / total * 100, 1) if total else 0

    absentismo_por_turma = sorted(
        (
            {'turma': turma, 'presentes': dados['presentes'], 'ausentes': dados['ausentes'],
             'justificadas': dados['justificadas']}
            for turma, dados in por_turma.items()
        ),
        key=lambda item: str(item['turma']),
    )

    alunos_mais_faltas = sorted(
        (
            {'aluno': aluno, 'total': total_faltas}
            for aluno, total_faltas in por_aluno.items()
        ),
        key=lambda item: item['total'],
        reverse=True,
    )[:10]

    contexto = {
        'atribuicoes': atribuicoes,
        'turmas': turmas,
        'mes': mes_str,
        'turma_id': turma_id,
        'presencas': presencas,
        'faltas': faltas,
        'justificadas': justificadas,
        'taxa_absentismo': taxa_absentismo,
        'absentismo_por_turma': absentismo_por_turma,
        'alunos_mais_faltas': alunos_mais_faltas,
        'estados_labels': ['Presenças', 'Faltas', 'Justificadas'],
        'estados_dados': [presencas, faltas, justificadas],
        'turma_labels': [str(item['turma']) for item in absentismo_por_turma],
        'turma_presentes': [item['presentes'] for item in absentismo_por_turma],
        'turma_ausentes': [item['ausentes'] for item in absentismo_por_turma],
        'turma_justificadas': [item['justificadas'] for item in absentismo_por_turma],
    }
    return render(request, 'frequencias/relatorio_assiduidade.html', contexto)


class JustificacaoListView(AdminOuProfessorRequeridoMixin, ListView):
    model = JustificacaoFalta
    template_name = 'frequencias/justificacoes.html'
    context_object_name = 'justificacoes'
    paginate_by = 20

    def get_queryset(self):
        queryset = JustificacaoFalta.objects.select_related(
            'frequencia__aluno',
            'frequencia__atribuicao__disciplina',
            'frequencia__atribuicao__turma',
        ).order_by('-data_submissao')

        if eh_administrador(self.request.user):
            return queryset
        return queryset.filter(frequencia__atribuicao__professor__user=self.request.user)


@admin_ou_professor_requerido
def justificacao_aprovar(request, pk):
    justificacao = get_object_or_404(JustificacaoFalta, pk=pk)

    if not eh_administrador(request.user) and \
            justificacao.frequencia.atribuicao.professor.user_id != request.user.id:
        return render(request, 'dashboards/sem_permissao.html', status=403)

    justificacao.aprovada = True
    justificacao.save()
    messages.success(request, 'Justificação aprovada.')
    return redirect('justificacao_lista')


def _pode_ver_justificacao(user, justificacao):
    if eh_administrador(user):
        return True
    if eh_professor(user):
        return justificacao.frequencia.atribuicao.professor.user_id == user.id
    if eh_aluno(user):
        aluno = getattr(user, 'aluno', None)
        return aluno is not None and justificacao.frequencia.aluno_id == aluno.id
    if eh_encarregado(user):
        encarregado = getattr(user, 'encarregado', None)
        return encarregado is not None and \
            justificacao.frequencia.aluno.encarregado_id == encarregado.id
    return False


@login_required
def justificacao_documento(request, pk):
    justificacao = get_object_or_404(
        JustificacaoFalta.objects.select_related(
            'frequencia__aluno__encarregado', 'frequencia__atribuicao__professor',
        ),
        pk=pk,
    )

    if not _pode_ver_justificacao(request.user, justificacao):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    if not justificacao.documento:
        raise Http404('Esta justificação não tem nenhum documento anexado.')

    tipo_conteudo, _ = mimetypes.guess_type(justificacao.documento.name)
    return FileResponse(
        justificacao.documento.open('rb'),
        content_type=tipo_conteudo or 'application/octet-stream',
        as_attachment=False,
        filename=justificacao.documento.name.rsplit('/', 1)[-1],
    )


def _pode_justificar(user, frequencia):
    if eh_aluno(user):
        aluno = getattr(user, 'aluno', None)
        return aluno is not None and frequencia.aluno_id == aluno.id
    if eh_encarregado(user):
        encarregado = getattr(user, 'encarregado', None)
        return encarregado is not None and frequencia.aluno.encarregado_id == encarregado.id
    return False


@login_required
def justificacao_criar(request, frequencia_id):
    frequencia = get_object_or_404(
        Frequencia.objects.select_related('aluno__encarregado', 'atribuicao__disciplina'),
        pk=frequencia_id,
    )

    if not _pode_justificar(request.user, frequencia):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    if frequencia.estado != Frequencia.FALTA:
        messages.error(request, 'Só é possível justificar registos marcados como falta.')
        return redirect('frequencia_lista')

    justificacao = getattr(frequencia, 'justificacaofalta', None)
    if justificacao and justificacao.aprovada:
        messages.info(request, 'Esta falta já tem uma justificação aprovada.')
        return redirect('frequencia_lista')

    if request.method == 'POST':
        form = JustificacaoFaltaForm(request.POST, request.FILES, instance=justificacao)
        if form.is_valid():
            nova_justificacao = form.save(commit=False)
            nova_justificacao.frequencia = frequencia
            nova_justificacao.save()
            messages.success(request, 'Justificação enviada com sucesso. Aguarde a aprovação do professor.')
            return redirect('frequencia_lista')
    else:
        form = JustificacaoFaltaForm(instance=justificacao)

    return render(request, 'frequencias/justificar.html', {
        'form': form,
        'frequencia': frequencia,
    })
