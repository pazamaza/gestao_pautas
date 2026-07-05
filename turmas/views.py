from django.urls import reverse_lazy
from django.views.generic import (ListView, CreateView,
    UpdateView)
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from accounts.mixins import AdministradorRequeridoMixin
from .models import Turma, PeriodoAcademico, AnoLetivo
from .forms import TurmaForm, PeriodoAcademicoForm

class TurmaListView(ListView):
    model = Turma
    template_name = 'turmas/lista.html'
    context_object_name = 'turmas'
    paginate_by = 10

    def get_queryset(self):
        queryset = Turma.objects.select_related('classe', 'ano_letivo').order_by(
            'classe__nome', 'nome'
        )

        pesquisa = self.request.GET.get('q')
        if pesquisa:
            queryset = queryset.filter(nome__icontains=pesquisa)

        ano_letivo_id = self.request.GET.get('ano_letivo')
        if ano_letivo_id:
            queryset = queryset.filter(ano_letivo_id=ano_letivo_id)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['anos_letivos'] = AnoLetivo.objects.all()
        return context

def desativar_turma(request, pk):
        turma = get_object_or_404(Turma, pk=pk)
        turma.ativo = False
        turma.save()
        messages.success( request, "Turma desativada com sucesso.")
        return redirect("turma_lista")

def reativar_turma(request, pk):
        turma = get_object_or_404(Turma, pk=pk)
        turma.ativo = True
        turma.save()
        messages.success( request, "Turma reativada com sucesso.")
        return redirect("turma_lista")
    
class TurmaCreateView(CreateView):
    model = Turma
    form_class = TurmaForm
    template_name = 'turmas/form.html'
    success_url = reverse_lazy(
        'turma_lista'
    )

class TurmaUpdateView(UpdateView):
    model = Turma
    form_class = TurmaForm
    template_name = 'turmas/form.html'
    success_url = reverse_lazy(
        'turma_lista'
    )

class TurmaInativaListView(ListView):

    model = Turma
    template_name = "turmas/inativas.html"

    def get_queryset(self):
        return Turma.objects.filter(ativo=False)


class PeriodoAcademicoListView(AdministradorRequeridoMixin, ListView):
    model = PeriodoAcademico
    template_name = 'turmas/periodo_lista.html'
    context_object_name = 'periodos'

    def get_queryset(self):
        return PeriodoAcademico.objects.select_related('ano_letivo').order_by(
            '-ano_letivo__descricao', 'nome'
        )


class PeriodoAcademicoCreateView(AdministradorRequeridoMixin, CreateView):
    model = PeriodoAcademico
    form_class = PeriodoAcademicoForm
    template_name = 'turmas/periodo_form.html'
    success_url = reverse_lazy('periodo_lista')


class PeriodoAcademicoUpdateView(AdministradorRequeridoMixin, UpdateView):
    model = PeriodoAcademico
    form_class = PeriodoAcademicoForm
    template_name = 'turmas/periodo_form.html'
    success_url = reverse_lazy('periodo_lista')