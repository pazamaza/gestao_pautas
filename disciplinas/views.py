from django.urls import reverse_lazy

from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
    DetailView, DetailView,
DeleteView
)
from django.contrib.auth.mixins import LoginRequiredMixin

from accounts.mixins import AdministradorRequeridoMixin
from .models import Disciplina
from .forms import DisciplinaForm


class DisciplinaListView(LoginRequiredMixin, ListView):

    model = Disciplina

    paginate_by = 10

    template_name = 'disciplinas/lista.html'

    context_object_name = 'disciplinas'

    def get_queryset(self):

        pesquisa = self.request.GET.get('q')

        queryset = Disciplina.objects.all()

        if pesquisa:

            queryset = queryset.filter(
                nome__icontains=pesquisa
            )

        return queryset


class DisciplinaCreateView(AdministradorRequeridoMixin, CreateView):

    model = Disciplina

    form_class = DisciplinaForm

    template_name = 'disciplinas/form.html'

    success_url = reverse_lazy(
        'disciplina_lista'
    )


class DisciplinaUpdateView(AdministradorRequeridoMixin, UpdateView):

    model = Disciplina

    form_class = DisciplinaForm

    template_name = 'disciplinas/form.html'

    success_url = reverse_lazy(
        'disciplina_lista'
    )


class DisciplinaDeleteView(AdministradorRequeridoMixin, DeleteView):

    model = Disciplina

    template_name = 'disciplinas/excluir.html'

    success_url = reverse_lazy(
        'disciplina_lista'
    )


class DisciplinaDetailView(LoginRequiredMixin, DetailView):

    model = Disciplina

    template_name = 'disciplinas/detalhe.html'

    context_object_name = 'disciplina'