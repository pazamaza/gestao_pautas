from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (ListView, CreateView,
    UpdateView, DeleteView)

from accounts.mixins import AdminOuProfessorRequeridoMixin
from accounts.utils import eh_administrador, eh_professor, eh_aluno, eh_encarregado
from .models import Frequencia
from .forms import FrequenciaForm


class FrequenciaListView(LoginRequiredMixin, ListView):
    model = Frequencia
    template_name = 'frequencias/lista.html'
    context_object_name = 'frequencias'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        queryset = Frequencia.objects.select_related(
            'aluno', 'atribuicao__professor__user',
            'atribuicao__disciplina', 'atribuicao__turma'
        ).order_by('-data')

        if eh_administrador(user):
            return queryset

        if eh_professor(user):
            return queryset.filter(atribuicao__professor__user=user)

        if eh_aluno(user):
            aluno = getattr(user, 'aluno', None)
            return queryset.filter(aluno=aluno) if aluno else queryset.none()

        if eh_encarregado(user):
            encarregado = getattr(user, 'encarregado', None)
            return queryset.filter(aluno__encarregado=encarregado) if encarregado else queryset.none()

        return queryset.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pode_gerir'] = (
            eh_administrador(self.request.user) or eh_professor(self.request.user)
        )
        return context


class FrequenciaCreateView(AdminOuProfessorRequeridoMixin, CreateView):
    model = Frequencia
    form_class = FrequenciaForm
    template_name = 'frequencias/form.html'
    success_url = reverse_lazy('frequencia_lista')


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
