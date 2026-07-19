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
        return context


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
    )
    if not eh_administrador(request.user):
        atribuicoes = atribuicoes.filter(professor__user=request.user)
    atribuicoes = atribuicoes.order_by('turma__classe__nome', 'turma__nome', 'disciplina__nome')

    contexto = {'atribuicoes': atribuicoes, 'atribuicao': None, 'data': None}

    if not atribuicoes.exists():
        messages.warning(request, 'Não existe nenhuma atribuição docente ativa associada a si.')
        return render(request, 'frequencias/lancamento.html', contexto)

    data_str = request.GET.get('data') or request.POST.get('data')
    try:
        data_selecionada = date.fromisoformat(data_str) if data_str else timezone.localdate()
    except ValueError:
        data_selecionada = timezone.localdate()
    contexto['data'] = data_selecionada

    dia_semana = DIA_SEMANA_POR_WEEKDAY.get(data_selecionada.weekday())
    atribuicoes_do_dia = (
        atribuicoes.filter(horarios__dia_semana=dia_semana).distinct()
        if dia_semana else atribuicoes.none()
    )
    contexto['atribuicoes_do_dia'] = atribuicoes_do_dia

    atribuicao_id = request.GET.get('atribuicao') or request.POST.get('atribuicao')
    atribuicao = atribuicoes_do_dia.filter(pk=atribuicao_id).first() if atribuicao_id else None

    if atribuicao is None:
        if atribuicao_id and request.method == 'POST':
            messages.error(
                request,
                'Esta disciplina não tem aula agendada nesta data, de acordo com o horário semanal — lançamento bloqueado.'
            )
            return redirect(f"{reverse('lancamento_frequencia')}?data={data_selecionada.isoformat()}")
        atribuicao = atribuicoes_do_dia.first()

    contexto['atribuicao'] = atribuicao

    if atribuicao is None:
        messages.info(
            request,
            'Não há aulas suas agendadas nesta data, de acordo com o horário semanal. Escolha outra data.'
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
                f"{reverse('lancamento_frequencia')}?atribuicao={atribuicao.id}&data={data_selecionada.isoformat()}"
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
