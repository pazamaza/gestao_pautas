from django.urls import reverse_lazy

from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DeleteView
)

from .models import Turma

from .forms import TurmaForm

class TurmaListView(ListView):

    model = Turma

    template_name = 'turmas/lista.html'

    context_object_name = 'turmas'

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

class TurmaDeleteView(DeleteView):

    model = Turma

    template_name = 'turmas/excluir.html'

    success_url = reverse_lazy(
        'turma_lista'
    )