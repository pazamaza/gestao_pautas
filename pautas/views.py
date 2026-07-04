from django.contrib import messages
from django.forms import modelformset_factory
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from alunos.models import Aluno
from turmas.models import Turma

from .forms import (
    AvaliacaoForm,
    ImportarNotasExcelForm,
    NotaForm,
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


class NotaListView(ListView):
    model = Nota
    template_name = 'pautas/lista_notas.html'
    context_object_name = 'notas'

    def get_queryset(self):
        return (
            Nota.objects
            .select_related(
                'aluno',
                'avaliacao__periodo',
                'avaliacao__atribuicao__disciplina',
                'avaliacao__atribuicao__turma',
            )
            .order_by('avaliacao__periodo__nome', 'aluno__nome')
        )


def pauta_turma(request, turma_id):
    turma = get_object_or_404(Turma, id=turma_id)
    alunos = Aluno.objects.filter(turma=turma, ativo=True).order_by('nome')
    context = {'turma': turma, 'alunos': alunos}
    return render(request, 'pautas/pauta_turma.html', context)


def pauta_lancamento(request):
    NotaFormSet = modelformset_factory(
        Nota,
        fields=('mac', 'npp', 'npt'),
        extra=5,
    )
    queryset = Nota.objects.all()

    if request.method == 'POST':
        formset = NotaFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Notas guardadas com sucesso.')
            return redirect('nota_lista')
    else:
        formset = NotaFormSet(queryset=queryset)

    return render(request, 'pautas/lancamento.html', {'formset': formset})


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
    notas = notas_da_avaliacao(avaliacao)

    return render(
        request,
        'pautas/pauta_trimestral.html',
        {
            'avaliacao': avaliacao,
            'notas': notas,
            'form_importacao': ImportarNotasExcelForm(),
        },
    )


def baixar_modelo_excel(request, avaliacao_id):
    avaliacao = get_object_or_404(Avaliacao, pk=avaliacao_id)
    arquivo = criar_modelo_excel(avaliacao)
    nome = f'modelo_pauta_{avaliacao.id}.xlsx'
    return FileResponse(
        arquivo,
        as_attachment=True,
        filename=nome,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


def exportar_excel(request, avaliacao_id):
    avaliacao = get_object_or_404(Avaliacao, pk=avaliacao_id)
    arquivo = exportar_pauta_excel(avaliacao, notas_da_avaliacao(avaliacao))
    nome = f'pauta_{avaliacao.id}.xlsx'
    return FileResponse(
        arquivo,
        as_attachment=True,
        filename=nome,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


def importar_excel(request, avaliacao_id):
    avaliacao = get_object_or_404(Avaliacao, pk=avaliacao_id)

    if request.method != 'POST':
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


def exportar_pdf(request, avaliacao_id):
    avaliacao = get_object_or_404(Avaliacao, pk=avaliacao_id)
    arquivo = exportar_pauta_pdf(avaliacao, notas_da_avaliacao(avaliacao))
    nome = f'pauta_{avaliacao.id}.pdf'
    return FileResponse(
        arquivo,
        as_attachment=True,
        filename=nome,
        content_type='application/pdf',
    )


def gerar_resultados(request):
    total = gerar_resultados_finais()
    messages.success(request, f'{total} resultados finais gerados com sucesso.')
    return redirect('resultado_lista')


class NotaCreateView(CreateView):
    model = Nota
    form_class = NotaForm
    template_name = 'pautas/forms.html'
    success_url = reverse_lazy('nota_lista')


class NotaUpdateView(UpdateView):
    model = Nota
    form_class = NotaForm
    template_name = 'pautas/forms.html'
    success_url = reverse_lazy('nota_lista')


class NotaDeleteView(DeleteView):
    model = Nota
    template_name = 'pautas/excluir.html'
    success_url = reverse_lazy('nota_lista')


class AvaliacaoListView(ListView):
    model = Avaliacao
    template_name = 'pautas/avaliacao_lista.html'
    context_object_name = 'avaliacoes'

    def get_queryset(self):
        return (
            Avaliacao.objects
            .select_related(
                'periodo',
                'atribuicao__professor__user',
                'atribuicao__disciplina',
                'atribuicao__turma',
            )
            .order_by('-criado_em')
        )


class AvaliacaoCreateView(CreateView):
    model = Avaliacao
    form_class = AvaliacaoForm
    template_name = 'pautas/avaliacao_form.html'
    success_url = reverse_lazy('avaliacao_lista')


class AvaliacaoUpdateView(UpdateView):
    model = Avaliacao
    form_class = AvaliacaoForm
    template_name = 'pautas/avaliacao_form.html'
    success_url = reverse_lazy('avaliacao_lista')


class AvaliacaoDeleteView(DeleteView):
    model = Avaliacao
    template_name = 'pautas/avaliacao_excluir.html'
    success_url = reverse_lazy('avaliacao_lista')


class ResultadoDisciplinaListView(ListView):
    model = ResultadoDisciplina
    template_name = 'pautas/resultado_lista.html'
    context_object_name = 'resultados'

    def get_queryset(self):
        return (
            ResultadoDisciplina.objects
            .select_related('aluno', 'disciplina', 'ano_letivo')
            .order_by('aluno__nome', 'disciplina__nome')
        )


class ResultadoDisciplinaCreateView(CreateView):
    model = ResultadoDisciplina
    form_class = ResultadoDisciplinaForm
    template_name = 'pautas/resultado_form.html'
    success_url = reverse_lazy('resultado_lista')


class ResultadoDisciplinaUpdateView(UpdateView):
    model = ResultadoDisciplina
    form_class = ResultadoDisciplinaForm
    template_name = 'pautas/resultado_form.html'
    success_url = reverse_lazy('resultado_lista')


class ResultadoDisciplinaDeleteView(DeleteView):
    model = ResultadoDisciplina
    template_name = 'pautas/resultado_excluir.html'
    success_url = reverse_lazy('resultado_lista')
