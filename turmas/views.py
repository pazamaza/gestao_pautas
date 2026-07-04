from django.urls import reverse_lazy
from django.views.generic import (ListView, CreateView,
    UpdateView)
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Turma
from .forms import TurmaForm

class TurmaListView(ListView):
    model = Turma
    def get_queryset(self):
        return Turma.objects.filter(ativo=True)
    template_name = 'turmas/lista.html'
    context_object_name = 'turmas'
    paginate_by = 10

    def get_queryset(self):
        pesquisa = self.request.GET.get('q')
        queryset = Turma.objects.all()
        if pesquisa:
            queryset = queryset.filter(     nome__icontains=pesquisa )
        return queryset
    
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