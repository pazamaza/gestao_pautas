from django.urls import reverse_lazy

from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
    DetailView
)

from django.contrib.messages.views import SuccessMessageMixin

from .models import Aluno

from .forms import AlunoForm

class AlunoListView(ListView):

    model = Aluno

    template_name = 'alunos/lista.html'

    context_object_name = 'alunos'

    paginate_by = 10

class AlunoCreateView(
    SuccessMessageMixin,
    CreateView
):

    model = Aluno

    form_class = AlunoForm

    template_name = 'alunos/forms.html'

    success_url = reverse_lazy(
        'aluno_lista'
    )

    success_message = (
        'Aluno cadastrado com sucesso.'
    )

class AlunoUpdateView(
    SuccessMessageMixin,
    UpdateView
):

    model = Aluno

    form_class = AlunoForm

    template_name = 'alunos/forms.html'

    success_url = reverse_lazy(
        'aluno_lista'
    )

    success_message = (
        'Aluno atualizado com sucesso.'
    )

class AlunoDetailView(DetailView):

    model = Aluno

    template_name = 'alunos/detalhe.html'

#Eliminar
class AlunoDeleteView(DeleteView):

    model = Aluno

    template_name = 'alunos/excluir.html'

    success_url = reverse_lazy(
        'aluno_lista'
    )

#Pesquisa
class AlunoListView(ListView):

    model = Aluno

    template_name = 'alunos/lista.html'

    context_object_name = 'alunos'

    paginate_by = 10

    def get_queryset(self):

        pesquisa = self.request.GET.get(
            'q'
        )

        queryset = Aluno.objects.all()

        if pesquisa:

            queryset = queryset.filter(
                nome__icontains=pesquisa
            )

        return queryset