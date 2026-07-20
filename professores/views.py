from django.db.models import Prefetch
from django.urls import reverse_lazy
from django.views.generic import (ListView, CreateView,
    UpdateView, DeleteView, DetailView)
from .models import (Professor, AtribuicaoDocente, DiretorTurma)

from .forms import (ProfessorForm, ProfessorUpdateForm,
    ProfessorCadastroForm, ProfessorEdicaoForm,
    AtribuicaoDocenteForm, DiretorTurmaForm)

from accounts.mixins import AdministradorRequeridoMixin
from django.contrib.auth.models import Group, User
from django.views import View
from django.shortcuts import (render, redirect)
from django.shortcuts import ( render,  redirect,
    get_object_or_404)
from django.views import View


class ProfessorCreateView(AdministradorRequeridoMixin, View):
    template_name = 'professores/cadastro.html'
    def get(self, request):
        form = ProfessorCadastroForm()
        return render(
            request,
            self.template_name,
            {'form': form}
        )
    def post(self, request):
        form = ProfessorCadastroForm(
            request.POST
        )
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data[
                    'username'
                ],
                password=form.cleaned_data[
                    'password'
                ],
                first_name=form.cleaned_data[
                    'first_name'
                ],
                last_name=form.cleaned_data[
                    'last_name'
                ],
                email=form.cleaned_data[
                    'email'
                ]
            )
            grupo_professor, _ = Group.objects.get_or_create(name='Professor')
            user.groups.add(grupo_professor)
            Professor.objects.create(
                user=user,
                numero_funcionario=
                form.cleaned_data[
                    'numero_funcionario'
                ],
                telefone=
                form.cleaned_data[
                    'telefone'
                ]
            )
            return redirect('professor_lista')
        return render(
            request,
            self.template_name,
            {'form': form}
        )


class ProfessorListView(AdministradorRequeridoMixin, ListView):
    model = Professor
    template_name = 'professores/lista.html'
    context_object_name = 'professores'

    def get_queryset(self):
        return Professor.objects.prefetch_related(
            Prefetch(
                'diretorturma_set',
                queryset=DiretorTurma.objects.filter(ativo=True).select_related('turma'),
                to_attr='diretorias_ativas'
            )
        )

class ProfessorUpdateView(AdministradorRequeridoMixin, View):

    template_name = 'professores/editar.html'

    def get(self, request, pk):

        professor = get_object_or_404(
            Professor,
            pk=pk
        )

        form = ProfessorEdicaoForm(
            initial={
                'first_name':
                professor.user.first_name,

                'last_name':
                professor.user.last_name,

                'email':
                professor.user.email,

                'numero_funcionario':
                professor.numero_funcionario,

                'telefone':
                professor.telefone,

                'ativo':
                professor.ativo,
            }
        )

        return render(
            request,
            self.template_name,
            {
                'form': form,
                'professor': professor
            }
        )

    def post(self, request, pk):

        professor = get_object_or_404(
            Professor,
            pk=pk
        )

        form = ProfessorEdicaoForm(
            request.POST
        )

        if form.is_valid():

            professor.user.first_name = (
                form.cleaned_data[
                    'first_name'
                ]
            )

            professor.user.last_name = (
                form.cleaned_data[
                    'last_name'
                ]
            )

            professor.user.email = (
                form.cleaned_data[
                    'email'
                ]
            )

            professor.user.save()

            professor.numero_funcionario = (
                form.cleaned_data[
                    'numero_funcionario'
                ]
            )

            professor.telefone = (
                form.cleaned_data[
                    'telefone'
                ]
            )

            professor.ativo = (
                form.cleaned_data[
                    'ativo'
                ]
            )

            professor.save()

            return redirect(
                'professor_lista'
            )

        return render(
            request,
            self.template_name,
            {
                'form': form,
                'professor': professor
            }
        )

class ProfessorDeleteView(AdministradorRequeridoMixin, DeleteView):
    model = Professor
    template_name = 'professores/excluir.html'
    success_url = reverse_lazy(
        'professor_lista'
    )

class AtribuicaoDocenteListView(AdministradorRequeridoMixin, ListView):
    model = AtribuicaoDocente
    template_name = (
        'professores/atribuicao_lista.html' )
    context_object_name = ('atribuicoes')

class AtribuicaoDocenteCreateView(AdministradorRequeridoMixin, CreateView):
    model = AtribuicaoDocente
    form_class = AtribuicaoDocenteForm
    template_name = ('professores/atribuicao_form.html' )
    success_url = reverse_lazy('atribuicao_lista')


class DiretorTurmaListView(AdministradorRequeridoMixin, ListView):
    model = DiretorTurma
    template_name = 'professores/diretor_turma_lista.html'
    context_object_name = 'diretores'

    def get_queryset(self):
        return DiretorTurma.objects.select_related(
            'professor__user', 'turma__classe', 'ano_letivo'
        ).order_by('-ano_letivo__descricao', 'turma__classe__nome', 'turma__nome')


class DiretorTurmaCreateView(AdministradorRequeridoMixin, CreateView):
    model = DiretorTurma
    form_class = DiretorTurmaForm
    template_name = 'professores/diretor_turma_form.html'
    success_url = reverse_lazy('diretor_turma_lista')


class DiretorTurmaUpdateView(AdministradorRequeridoMixin, UpdateView):
    model = DiretorTurma
    form_class = DiretorTurmaForm
    template_name = 'professores/diretor_turma_form.html'
    success_url = reverse_lazy('diretor_turma_lista')