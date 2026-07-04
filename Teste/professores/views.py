from django.urls import reverse_lazy
from django.views.generic import (ListView, CreateView,
    UpdateView, DeleteView, DetailView)
from .models import (Professor, AtribuicaoDocente)
from .forms import (ProfessorForm, AtribuicaoDocenteForm, ProfessorUpdateForm)

class ProfessorListView(ListView):
    model = Professor
    paginate_by = 10
    template_name = 'professores/lista.html'
    context_object_name = 'professores'

class ProfessorCreateView(CreateView):
    model = Professor
    form_class = ProfessorForm
    template_name = 'professores/forms.html'
    success_url = reverse_lazy(
        'professor_lista' )

class ProfessorUpdateView(UpdateView):
    model = Professor
    form_class = ProfessorUpdateForm
    template_name = 'professores/forms.html'
    success_url = reverse_lazy(
        'professor_lista'
    )


class ProfessorDeleteView(DeleteView):
    model = Professor
    template_name = 'professores/excluir.html'
    success_url = reverse_lazy(
        'professor_lista'
    )

class AtribuicaoDocenteListView(ListView):
    model = AtribuicaoDocente
    template_name = (
        'professores/atribuicao_lista.html' )
    context_object_name = ('atribuicoes')

class AtribuicaoDocenteCreateView(CreateView):
    model = AtribuicaoDocente
    form_class = AtribuicaoDocenteForm
    template_name = ('professores/atribuicao_forms.html' )
    success_url = reverse_lazy('atribuicao_lista')