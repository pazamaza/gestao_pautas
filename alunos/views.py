from django.contrib import messages
from django.db.models import ProtectedError
from django.urls import reverse_lazy
from django.views.generic import (ListView, CreateView,
    UpdateView, DeleteView, DetailView)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from .models import ( Aluno, Encarregado)
from .forms import (AlunoForm, EncarregadoCadastroForm, EncarregadoEdicaoForm)
from django.contrib.auth.models import Group, User
from django.shortcuts import (render, redirect,
    get_object_or_404)
from django.views import View
from accounts.utils import eh_subdiretor_pedagogico, eh_professor
from accounts.mixins import SubdiretorPedagogicoRequeridoMixin, AdminOuProfessorRequeridoMixin
from professores.models import AtribuicaoDocente
from turmas.models import Turma


class AlunoCreateView(SubdiretorPedagogicoRequeridoMixin, SuccessMessageMixin, CreateView):
    model = Aluno
    form_class = AlunoForm
    template_name = 'alunos/forms.html'
    success_url = reverse_lazy('aluno_lista' )
    success_message = ('Aluno cadastrado com sucesso.' )

class AlunoUpdateView(SubdiretorPedagogicoRequeridoMixin, SuccessMessageMixin, UpdateView):
    model = Aluno
    form_class = AlunoForm
    template_name = 'alunos/forms.html'
    success_url = reverse_lazy('aluno_lista' )
    success_message = ('Aluno atualizado com sucesso.' )

class AlunoDetailView(AdminOuProfessorRequeridoMixin, DetailView):
    model = Aluno
    template_name = 'alunos/detalhe.html'
#Eliminar
class AlunoDeleteView(SubdiretorPedagogicoRequeridoMixin, DeleteView):
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
        if eh_subdiretor_pedagogico(user):
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

class EncarregadoListView(SubdiretorPedagogicoRequeridoMixin, ListView):
    model = Encarregado
    template_name = 'encarregados/lista.html'
    context_object_name = 'encarregados'
    paginate_by = 10

    def get_queryset(self):
        return Encarregado.objects.select_related('user').order_by('user__first_name', 'user__last_name')

class EncarregadoCreateView(SubdiretorPedagogicoRequeridoMixin, View):
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


class EncarregadoDetailView(SubdiretorPedagogicoRequeridoMixin, DetailView):
    model = Encarregado
    template_name = 'encarregados/detalhe.html'
    context_object_name = 'encarregado'


class EncarregadoUpdateView(SubdiretorPedagogicoRequeridoMixin, View):
    template_name = 'encarregados/editar.html'

    def get(self, request, pk):
        encarregado = get_object_or_404(Encarregado, pk=pk)
        form = EncarregadoEdicaoForm(initial={
            'first_name': encarregado.user.first_name,
            'last_name': encarregado.user.last_name,
            'email': encarregado.user.email,
            'telefone': encarregado.telefone,
            'profissao': encarregado.profissao,
        })
        return render(request, self.template_name, {'form': form, 'encarregado': encarregado})

    def post(self, request, pk):
        encarregado = get_object_or_404(Encarregado, pk=pk)
        form = EncarregadoEdicaoForm(request.POST)
        if form.is_valid():
            encarregado.user.first_name = form.cleaned_data['first_name']
            encarregado.user.last_name = form.cleaned_data['last_name']
            encarregado.user.email = form.cleaned_data['email']
            encarregado.user.save()

            encarregado.telefone = form.cleaned_data['telefone']
            encarregado.profissao = form.cleaned_data['profissao']
            encarregado.save()

            messages.success(request, 'Encarregado atualizado com sucesso.')
            return redirect('encarregado_lista')
        return render(request, self.template_name, {'form': form, 'encarregado': encarregado})


class EncarregadoDeleteView(SubdiretorPedagogicoRequeridoMixin, DeleteView):
    model = Encarregado
    template_name = 'encarregados/excluir.html'
    context_object_name = 'encarregado'
    success_url = reverse_lazy('encarregado_lista')

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request,
                'Não é possível eliminar este encarregado: existem alunos associados a ele.'
            )
            return redirect('encarregado_lista')

