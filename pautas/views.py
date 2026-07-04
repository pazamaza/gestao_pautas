from django.contrib import messages
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.decoracors import (
    admin_ou_professor_requerido,
    administrador_requerido,
    aluno_requerido,
    encarregado_requerido,
    professor_requerido,
)
from accounts.mixins import (
    AdminOuProfessorRequeridoMixin,
    ProfessorRequeridoMixin,
    SuperuserRequeridoMixin,
)
from accounts.utils import eh_administrador
from alunos.models import Aluno
from disciplinas.models import Disciplina
from professores.models import AtribuicaoDocente, DiretorTurma
from turmas.models import AnoLetivo, PeriodoAcademico, Turma
from notificacoes.services import notificar_erro_pauta

from .forms import (
    AvaliacaoForm,
    ImportarNotasExcelForm,
    NotaForm,
    ObservacoesValidacaoForm,
    ResultadoDisciplinaForm,
)
from .models import Avaliacao, Nota, ResultadoDisciplina
from .services.excel import (
    criar_modelo_excel,
    exportar_pauta_excel,
    importar_notas_excel,
)
from .services.pdf import exportar_pauta_pdf
from .services.resultados import gerar_resultados_finais


def notas_da_avaliacao(avaliacao):
    return (
        Nota.objects
        .filter(avaliacao=avaliacao)
        .select_related('aluno')
        .order_by('aluno__nome')
    )


def _pode_ver_avaliacao(user, avaliacao):
    return eh_administrador(user) or avaliacao.atribuicao.professor.user_id == user.id


class NotaListView(AdminOuProfessorRequeridoMixin, ListView):
    model = Nota
    template_name = 'pautas/lista_notas.html'
    context_object_name = 'notas'

    def get_queryset(self):
        queryset = (
            Nota.objects
            .select_related(
                'aluno',
                'avaliacao__periodo',
                'avaliacao__atribuicao__disciplina',
                'avaliacao__atribuicao__turma',
            )
            .order_by('avaliacao__periodo__nome', 'aluno__nome')
        )

        if not eh_administrador(self.request.user):
            queryset = queryset.filter(
                avaliacao__atribuicao__professor__user=self.request.user
            )

        return queryset


@admin_ou_professor_requerido
def pauta_turma(request, turma_id):
    turma = get_object_or_404(Turma, id=turma_id)
    alunos = Aluno.objects.filter(turma=turma, ativo=True).order_by('nome')
    context = {'turma': turma, 'alunos': alunos}
    return render(request, 'pautas/pauta_turma.html', context)


@admin_ou_professor_requerido
def pauta_trimestral(request, avaliacao_id):
    avaliacao = get_object_or_404(
        Avaliacao.objects.select_related(
            'periodo',
            'atribuicao__professor__user',
            'atribuicao__disciplina',
            'atribuicao__turma',
            'atribuicao__ano_letivo',
        ),
        pk=avaliacao_id,
    )

    if not _pode_ver_avaliacao(request.user, avaliacao):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    notas = notas_da_avaliacao(avaliacao)

    return render(
        request,
        'pautas/pauta_trimestral.html',
        {
            'avaliacao': avaliacao,
            'notas': notas,
            'form_importacao': ImportarNotasExcelForm(),
            'form_erro_validacao': ObservacoesValidacaoForm(),
            'eh_administrador': eh_administrador(request.user),
        },
    )


@admin_ou_professor_requerido
def baixar_modelo_excel(request, avaliacao_id):
    avaliacao = get_object_or_404(Avaliacao, pk=avaliacao_id)

    if not _pode_ver_avaliacao(request.user, avaliacao):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    arquivo = criar_modelo_excel(avaliacao)
    nome = f'modelo_pauta_{avaliacao.id}.xlsx'
    return FileResponse(
        arquivo,
        as_attachment=True,
        filename=nome,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@admin_ou_professor_requerido
def exportar_excel(request, avaliacao_id):
    avaliacao = get_object_or_404(Avaliacao, pk=avaliacao_id)

    if not _pode_ver_avaliacao(request.user, avaliacao):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    arquivo = exportar_pauta_excel(avaliacao, notas_da_avaliacao(avaliacao))
    nome = f'pauta_{avaliacao.id}.xlsx'
    return FileResponse(
        arquivo,
        as_attachment=True,
        filename=nome,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@professor_requerido
def importar_excel(request, avaliacao_id):
    avaliacao = get_object_or_404(
        Avaliacao.objects.select_related('periodo', 'atribuicao__professor__user'),
        pk=avaliacao_id,
    )

    if avaliacao.atribuicao.professor.user_id != request.user.id:
        return render(request, 'dashboards/sem_permissao.html', status=403)

    if request.method != 'POST':
        return redirect('pauta_trimestral', avaliacao_id=avaliacao.id)

    if not avaliacao.periodo.periodo_lancamento_ativo():
        messages.error(request, 'Fora do período de lançamento de notas para este trimestre.')
        return redirect('pauta_trimestral', avaliacao_id=avaliacao.id)

    form = ImportarNotasExcelForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, 'Selecione um arquivo Excel valido.')
        return redirect('pauta_trimestral', avaliacao_id=avaliacao.id)

    resultado = importar_notas_excel(
        avaliacao,
        form.cleaned_data['arquivo'],
    )

    if resultado['erros']:
        for erro in resultado['erros'][:5]:
            messages.warning(request, erro)
        if len(resultado['erros']) > 5:
            messages.warning(
                request,
                f"Existem mais {len(resultado['erros']) - 5} erros no arquivo.",
            )

    messages.success(
        request,
        (
            f"Importacao concluida: {resultado['criados']} notas criadas e "
            f"{resultado['atualizados']} atualizadas."
        ),
    )
    return redirect('pauta_trimestral', avaliacao_id=avaliacao.id)


@admin_ou_professor_requerido
def exportar_pdf(request, avaliacao_id):
    avaliacao = get_object_or_404(Avaliacao, pk=avaliacao_id)

    if not _pode_ver_avaliacao(request.user, avaliacao):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    arquivo = exportar_pauta_pdf(avaliacao, notas_da_avaliacao(avaliacao))
    nome = f'pauta_{avaliacao.id}.pdf'
    return FileResponse(
        arquivo,
        as_attachment=True,
        filename=nome,
        content_type='application/pdf',
    )


@administrador_requerido
def gerar_resultados(request):
    total = gerar_resultados_finais()
    messages.success(request, f'{total} resultados finais gerados com sucesso.')
    return redirect('resultado_lista')


@administrador_requerido
def avaliacao_validar(request, avaliacao_id):
    avaliacao = get_object_or_404(Avaliacao, pk=avaliacao_id)
    avaliacao.marcar_validada(request.user)
    messages.success(request, 'Avaliação validada e disponibilizada.')
    return redirect('pauta_trimestral', avaliacao_id=avaliacao.id)


@administrador_requerido
def avaliacao_reportar_erro(request, avaliacao_id):
    avaliacao = get_object_or_404(
        Avaliacao.objects.select_related(
            'atribuicao__professor__user',
            'atribuicao__turma',
            'atribuicao__disciplina',
            'atribuicao__ano_letivo',
        ),
        pk=avaliacao_id,
    )

    if request.method != 'POST':
        return redirect('pauta_trimestral', avaliacao_id=avaliacao.id)

    form = ObservacoesValidacaoForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Indique as observações do erro encontrado.')
        return redirect('pauta_trimestral', avaliacao_id=avaliacao.id)

    observacoes = form.cleaned_data['observacoes_validacao']
    avaliacao.marcar_com_erros(request.user, observacoes)

    diretor = DiretorTurma.objects.filter(
        turma=avaliacao.atribuicao.turma,
        ano_letivo=avaliacao.atribuicao.ano_letivo,
        ativo=True,
    ).select_related('professor__user').first()

    if not diretor:
        messages.warning(request, 'Não há diretor de turma definido; apenas o professor foi notificado.')

    notificar_erro_pauta(
        professor_user=avaliacao.atribuicao.professor.user,
        diretor_user=diretor.professor.user if diretor else None,
        titulo=f'Erros na pauta de {avaliacao.atribuicao.disciplina} - {avaliacao.atribuicao.turma}',
        mensagem=observacoes,
        link_url=reverse('pauta_trimestral', kwargs={'avaliacao_id': avaliacao.id}),
    )

    messages.success(request, 'Erro reportado e professor/diretor notificados.')
    return redirect('avaliacao_lista')


@administrador_requerido
def resultado_validar(request, pk):
    resultado = get_object_or_404(ResultadoDisciplina, pk=pk)
    resultado.marcar_validada(request.user)
    messages.success(request, 'Resultado final validado e disponibilizado.')
    return redirect('resultado_lista')


@administrador_requerido
def resultado_reportar_erro(request, pk):
    resultado = get_object_or_404(
        ResultadoDisciplina.objects.select_related('aluno__turma', 'disciplina', 'ano_letivo'),
        pk=pk,
    )

    if request.method != 'POST':
        return redirect('resultado_lista')

    form = ObservacoesValidacaoForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Indique as observações do erro encontrado.')
        return redirect('resultado_lista')

    observacoes = form.cleaned_data['observacoes_validacao']
    resultado.marcar_com_erros(request.user, observacoes)

    atribuicao = AtribuicaoDocente.objects.filter(
        disciplina=resultado.disciplina,
        turma=resultado.aluno.turma,
        ano_letivo=resultado.ano_letivo,
        ativo=True,
    ).select_related('professor__user').first()

    diretor = DiretorTurma.objects.filter(
        turma=resultado.aluno.turma,
        ano_letivo=resultado.ano_letivo,
        ativo=True,
    ).select_related('professor__user').first()

    if not atribuicao:
        messages.warning(request, 'Não foi encontrada a atribuição docente correspondente; verifique manualmente.')
    if not diretor:
        messages.warning(request, 'Não há diretor de turma definido para esta turma/ano.')

    notificar_erro_pauta(
        professor_user=atribuicao.professor.user if atribuicao else None,
        diretor_user=diretor.professor.user if diretor else None,
        titulo=f'Erros no resultado final de {resultado.disciplina} - {resultado.aluno.turma}',
        mensagem=observacoes,
        link_url=reverse('resultado_lista'),
    )

    messages.success(request, 'Erro reportado e notificações enviadas.')
    return redirect('resultado_lista')


class NotaCreateView(ProfessorRequeridoMixin, CreateView):
    model = Nota
    form_class = NotaForm
    template_name = 'pautas/forms.html'
    success_url = reverse_lazy('nota_lista')


class NotaUpdateView(ProfessorRequeridoMixin, UpdateView):
    model = Nota
    form_class = NotaForm
    template_name = 'pautas/forms.html'
    success_url = reverse_lazy('nota_lista')

    def get_queryset(self):
        return Nota.objects.filter(avaliacao__atribuicao__professor__user=self.request.user)


class NotaDeleteView(ProfessorRequeridoMixin, DeleteView):
    model = Nota
    template_name = 'pautas/excluir.html'
    success_url = reverse_lazy('nota_lista')

    def get_queryset(self):
        return Nota.objects.filter(avaliacao__atribuicao__professor__user=self.request.user)


class AvaliacaoListView(AdminOuProfessorRequeridoMixin, ListView):
    model = Avaliacao
    template_name = 'pautas/avaliacao_lista.html'
    context_object_name = 'avaliacoes'

    def get_queryset(self):
        queryset = (
            Avaliacao.objects
            .select_related(
                'periodo',
                'atribuicao__professor__user',
                'atribuicao__disciplina',
                'atribuicao__turma',
            )
            .order_by('-criado_em')
        )

        if not eh_administrador(self.request.user):
            queryset = queryset.filter(atribuicao__professor__user=self.request.user)

        turma_id = self.request.GET.get('turma')
        disciplina_id = self.request.GET.get('disciplina')
        periodo_id = self.request.GET.get('periodo')
        status = self.request.GET.get('status')

        if turma_id:
            queryset = queryset.filter(atribuicao__turma_id=turma_id)
        if disciplina_id:
            queryset = queryset.filter(atribuicao__disciplina_id=disciplina_id)
        if periodo_id:
            queryset = queryset.filter(periodo_id=periodo_id)
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['turmas'] = Turma.objects.filter(ativo=True).order_by('classe__nome', 'nome')
        context['disciplinas'] = Disciplina.objects.all().order_by('nome')
        context['periodos'] = PeriodoAcademico.objects.select_related('ano_letivo').order_by(
            '-ano_letivo__descricao', 'nome'
        )
        context['status_choices'] = Avaliacao.STATUS_CHOICES
        context['eh_administrador'] = eh_administrador(self.request.user)
        return context


class AvaliacaoCreateView(ProfessorRequeridoMixin, CreateView):
    model = Avaliacao
    form_class = AvaliacaoForm
    template_name = 'pautas/avaliacao_form.html'
    success_url = reverse_lazy('avaliacao_lista')


class AvaliacaoUpdateView(ProfessorRequeridoMixin, UpdateView):
    model = Avaliacao
    form_class = AvaliacaoForm
    template_name = 'pautas/avaliacao_form.html'
    success_url = reverse_lazy('avaliacao_lista')

    def get_queryset(self):
        return Avaliacao.objects.filter(atribuicao__professor__user=self.request.user)


class AvaliacaoDeleteView(ProfessorRequeridoMixin, DeleteView):
    model = Avaliacao
    template_name = 'pautas/avaliacao_excluir.html'
    success_url = reverse_lazy('avaliacao_lista')

    def get_queryset(self):
        return Avaliacao.objects.filter(atribuicao__professor__user=self.request.user)


class ResultadoDisciplinaListView(AdminOuProfessorRequeridoMixin, ListView):
    model = ResultadoDisciplina
    template_name = 'pautas/resultado_lista.html'
    context_object_name = 'resultados'

    def get_queryset(self):
        queryset = (
            ResultadoDisciplina.objects
            .select_related('aluno', 'aluno__turma', 'disciplina', 'ano_letivo')
            .order_by('aluno__nome', 'disciplina__nome')
        )

        if not eh_administrador(self.request.user):
            disciplinas_professor = AtribuicaoDocente.objects.filter(
                professor__user=self.request.user
            ).values('disciplina')
            queryset = queryset.filter(disciplina__in=disciplinas_professor)

        turma_id = self.request.GET.get('turma')
        disciplina_id = self.request.GET.get('disciplina')
        ano_letivo_id = self.request.GET.get('ano_letivo')
        status = self.request.GET.get('status')

        if turma_id:
            queryset = queryset.filter(aluno__turma_id=turma_id)
        if disciplina_id:
            queryset = queryset.filter(disciplina_id=disciplina_id)
        if ano_letivo_id:
            queryset = queryset.filter(ano_letivo_id=ano_letivo_id)
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['turmas'] = Turma.objects.filter(ativo=True).order_by('classe__nome', 'nome')
        context['disciplinas'] = Disciplina.objects.all().order_by('nome')
        context['anos_letivos'] = AnoLetivo.objects.all()
        context['status_choices'] = ResultadoDisciplina.STATUS_CHOICES
        context['eh_administrador'] = eh_administrador(self.request.user)
        return context


class ResultadoDisciplinaCreateView(SuperuserRequeridoMixin, CreateView):
    model = ResultadoDisciplina
    form_class = ResultadoDisciplinaForm
    template_name = 'pautas/resultado_form.html'
    success_url = reverse_lazy('resultado_lista')


class ResultadoDisciplinaUpdateView(SuperuserRequeridoMixin, UpdateView):
    model = ResultadoDisciplina
    form_class = ResultadoDisciplinaForm
    template_name = 'pautas/resultado_form.html'
    success_url = reverse_lazy('resultado_lista')


class ResultadoDisciplinaDeleteView(SuperuserRequeridoMixin, DeleteView):
    model = ResultadoDisciplina
    template_name = 'pautas/resultado_excluir.html'
    success_url = reverse_lazy('resultado_lista')


def _pautas_validadas_do_aluno(aluno):
    resultados_por_disciplina = {
        resultado.disciplina_id: resultado
        for resultado in ResultadoDisciplina.objects.filter(
            aluno=aluno, status=ResultadoDisciplina.STATUS_VALIDADA
        ).select_related('disciplina', 'ano_letivo')
    }

    notas = (
        Nota.objects
        .filter(aluno=aluno, avaliacao__status=Avaliacao.STATUS_VALIDADA)
        .select_related(
            'avaliacao__periodo',
            'avaliacao__atribuicao__disciplina',
        )
        .order_by('avaliacao__atribuicao__disciplina__nome', 'avaliacao__periodo__nome')
    )

    disciplinas = {}
    for nota in notas:
        disciplina = nota.avaliacao.atribuicao.disciplina
        info = disciplinas.setdefault(disciplina.id, {
            'disciplina': disciplina,
            'notas': [],
            'resultado': resultados_por_disciplina.get(disciplina.id),
        })
        info['notas'].append(nota)

    for disciplina_id, resultado in resultados_por_disciplina.items():
        if disciplina_id not in disciplinas:
            disciplinas[disciplina_id] = {
                'disciplina': resultado.disciplina,
                'notas': [],
                'resultado': resultado,
            }

    return {
        'disciplinas': sorted(disciplinas.values(), key=lambda info: info['disciplina'].nome),
    }


@aluno_requerido
def minhas_notas(request):
    aluno = getattr(request.user, 'aluno', None)

    if aluno is None:
        return render(request, 'pautas/minhas_notas.html', {'aluno': None})

    contexto = _pautas_validadas_do_aluno(aluno)
    contexto['aluno'] = aluno
    return render(request, 'pautas/minhas_notas.html', contexto)


@encarregado_requerido
def meus_dependentes(request):
    dependentes = Aluno.objects.filter(
        encarregado=request.user.encarregado
    ).order_by('nome')
    return render(request, 'pautas/meus_dependentes.html', {'dependentes': dependentes})


@encarregado_requerido
def notas_dependente(request, aluno_id):
    aluno = get_object_or_404(Aluno.objects.select_related('encarregado__user'), pk=aluno_id)

    if aluno.encarregado.user_id != request.user.id:
        return render(request, 'dashboards/sem_permissao.html', status=403)

    contexto = _pautas_validadas_do_aluno(aluno)
    contexto['aluno'] = aluno
    return render(request, 'pautas/minhas_notas.html', contexto)
