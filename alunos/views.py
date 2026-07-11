from django.urls import reverse_lazy
from django.views.generic import (ListView, CreateView,
    UpdateView, DeleteView, DetailView)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from .models import ( Aluno, Encarregado)
from .forms import (AlunoForm, EncarregadoCadastroForm)
from django.contrib.auth.models import Group, User
from django.shortcuts import (render, redirect,
    get_object_or_404)
from django.views import View
from accounts.utils import eh_administrador, eh_professor
from professores.models import AtribuicaoDocente
from turmas.models import Turma


class AlunoCreateView(SuccessMessageMixin, CreateView):
    model = Aluno
    form_class = AlunoForm
    template_name = 'alunos/forms.html'
    success_url = reverse_lazy('aluno_lista' )
    success_message = ('Aluno cadastrado com sucesso.' )

class AlunoUpdateView(SuccessMessageMixin, UpdateView):
    model = Aluno
    form_class = AlunoForm
    template_name = 'alunos/forms.html'
    success_url = reverse_lazy('aluno_lista' )
    success_message = ('Aluno atualizado com sucesso.' )

class AlunoDetailView(DetailView):
    model = Aluno
    template_name = 'alunos/detalhe.html'
#Eliminar
class AlunoDeleteView(DeleteView):
    model = Aluno
    template_name = 'alunos/excluir.html'
    success_url = reverse_lazy('aluno_lista' )

#Pesquisa
class AlunoListView(LoginRequiredMixin, ListView):
    model = Aluno
    template_name = 'alunos/lista.html'
    context_object_name = 'alunos'
    paginate_by = 10
    def get_turmas_permitidas(self):
        user = self.request.user
        if eh_administrador(user):
            return Turma.objects.filter(ativo=True).order_by('classe__nome', 'nome')
        if eh_professor(user):
            turmas_ids = AtribuicaoDocente.objects.filter(
                professor__user=user, ativo=True
            ).values_list('turma_id', flat=True)
            return Turma.objects.filter(id__in=turmas_ids).order_by('classe__nome', 'nome')
        return Turma.objects.none()

    def get_queryset(self):
        pesquisa = self.request.GET.get('q')
        turma_id = self.request.GET.get('turma')
        turmas_permitidas = self.get_turmas_permitidas()
        queryset = Aluno.objects.filter(turma__in=turmas_permitidas).order_by('nome')

        if turma_id:
            queryset = queryset.filter(turma_id=turma_id)

        if pesquisa:
            queryset = queryset.filter(
                nome__icontains=pesquisa
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['turmas'] = self.get_turmas_permitidas()
        return context

class EncarregadoListView(ListView):
    model = Encarregado
    template_name = 'encarregados/lista.html'
    context_object_name = 'encarregados'
    paginate_by = 10

class EncarregadoCreateView(View):
    template_name = 'encarregados/cadastro.html'
    def get(self, request):
        form = EncarregadoCadastroForm()
        return render( request,
            self.template_name, {'form': form})
    def post(self, request):
        form = EncarregadoCadastroForm(
            request.POST )
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data[
                    'username' ],
                password=form.cleaned_data[
                    'password' ],
                first_name=form.cleaned_data[
                    'first_name'],
                last_name=form.cleaned_data[
                    'last_name' ],
                email=form.cleaned_data[
                    'email' ] )
            grupo_encarregado, _ = Group.objects.get_or_create(name='Encarregado')
            user.groups.add(grupo_encarregado)
            Encarregado.objects.create(
                user=user,
                telefone=form.cleaned_data[
                    'telefone' ],
                profissao=form.cleaned_data[           'profissao' ] )
            return redirect('encarregado_lista')
        return render(request,  self.template_name,
            {'form': form} )
    
