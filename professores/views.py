from django.urls import reverse_lazy
from django.views.generic import (ListView, CreateView,
    UpdateView, DeleteView, DetailView)
from .models import (Professor, AtribuicaoDocente, DiretorTurma)
from turmas.models import AnoLetivo, Turma

from .forms import (ProfessorForm, ProfessorUpdateForm,
    ProfessorCadastroForm, ProfessorEdicaoForm,
    AtribuicaoDocenteForm, DiretorTurmaForm)

from accounts.mixins import AdministradorRequeridoMixin
from accounts.decoracors import administrador_requerido
from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.views import View
from django.shortcuts import (render, redirect,
    get_object_or_404)


def _juntar_com_e(itens):
    itens = sorted(itens)
    if not itens:
        return None
    if len(itens) == 1:
        return itens[0]
    return ', '.join(itens[:-1]) + ' e ' + itens[-1]


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


class ProfessorDetailView(AdministradorRequeridoMixin, DetailView):
    model = Professor
    template_name = 'professores/detalhe.html'
    context_object_name = 'professor'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['diretorias_ativas'] = DiretorTurma.objects.filter(
            professor=self.object, ativo=True
        ).select_related('turma')
        return context


class ProfessorListView(AdministradorRequeridoMixin, ListView):
    model = Professor
    template_name = 'professores/lista.html'
    context_object_name = 'professores'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        linhas_professores = []
        for professor in context['professores']:
            atribuicoes = AtribuicaoDocente.objects.filter(
                professor=professor, ativo=True
            ).select_related('disciplina', 'turma__classe')

            niveis_por_disciplina = {}
            for atr in atribuicoes:
                niveis_por_disciplina.setdefault(atr.disciplina, set()).add(atr.turma.classe.nome)

            disciplinas = [
                {'disciplina': disciplina, 'turmas': _juntar_com_e(niveis)}
                for disciplina, niveis in niveis_por_disciplina.items()
            ] or [{'disciplina': None, 'turmas': None}]

            diretorias = DiretorTurma.objects.filter(
                professor=professor, ativo=True
            ).select_related('turma')

            linhas_professores.append({
                'professor': professor,
                'disciplinas': disciplinas,
                'rowspan': len(disciplinas),
                'dir_turma': _juntar_com_e([str(d.turma) for d in diretorias]),
            })

        context['linhas_professores'] = linhas_professores
        return context

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

    def get_queryset(self):
        return AtribuicaoDocente.objects.select_related(
            'professor__user', 'disciplina', 'turma__classe', 'ano_letivo'
        ).order_by('professor__user__first_name', 'professor__user__username', 'disciplina__nome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        atribuicoes = list(context['atribuicoes'])

        ano_letivo = AnoLetivo.objects.filter(ativo=True).first() or AnoLetivo.objects.first()

        turmas = list(
            Turma.objects.filter(ano_letivo=ano_letivo, ativo=True)
            .select_related('classe')
            .order_by('classe__nome', 'nome')
        ) if ano_letivo else []

        colunas_classes = []
        classe_atual_id = None
        for turma in turmas:
            if turma.classe_id != classe_atual_id:
                classe_atual_id = turma.classe_id
                colunas_classes.append({'classe': turma.classe, 'turmas': []})
            colunas_classes[-1]['turmas'].append(turma)

        mapa_celulas = {
            (atr.professor_id, atr.disciplina_id, atr.turma_id): atr
            for atr in atribuicoes
        }

        linhas = []
        vistos = set()
        for atr in atribuicoes:
            chave = (atr.professor_id, atr.disciplina_id)
            if chave in vistos:
                continue
            vistos.add(chave)
            linhas.append({
                'professor': atr.professor,
                'disciplina': atr.disciplina,
                'celulas': [
                    mapa_celulas.get((atr.professor_id, atr.disciplina_id, turma.id))
                    for turma in turmas
                ],
            })

        blocos_professores = []
        professor_atual_id = None
        for linha in linhas:
            if linha['professor'].id != professor_atual_id:
                professor_atual_id = linha['professor'].id
                blocos_professores.append({'professor': linha['professor'], 'linhas': []})
            blocos_professores[-1]['linhas'].append(linha)

        for bloco in blocos_professores:
            bloco['rowspan'] = len(bloco['linhas'])

        context['ano_letivo'] = ano_letivo
        context['colunas_classes'] = colunas_classes
        context['blocos_professores'] = blocos_professores
        return context

class AtribuicaoDocenteCreateView(AdministradorRequeridoMixin, CreateView):
    model = AtribuicaoDocente
    form_class = AtribuicaoDocenteForm
    template_name = ('professores/atribuicao_form.html' )
    success_url = reverse_lazy('atribuicao_lista')
    initial = {'ativo': True}


class AtribuicaoDocenteDetailView(AdministradorRequeridoMixin, DetailView):
    model = AtribuicaoDocente
    template_name = 'professores/atribuicao_detalhe.html'
    context_object_name = 'atribuicao'


class AtribuicaoDocenteUpdateView(AdministradorRequeridoMixin, UpdateView):
    model = AtribuicaoDocente
    form_class = AtribuicaoDocenteForm
    template_name = 'professores/atribuicao_form.html'
    success_url = reverse_lazy('atribuicao_lista')


@administrador_requerido
def atribuicao_desativar(request, pk):
    atribuicao = get_object_or_404(AtribuicaoDocente, pk=pk)
    atribuicao.ativo = False
    atribuicao.save()
    messages.success(request, 'Atribuição desativada com sucesso.')
    return redirect('atribuicao_lista')


@administrador_requerido
def atribuicao_reativar(request, pk):
    atribuicao = get_object_or_404(AtribuicaoDocente, pk=pk)
    atribuicao.ativo = True
    atribuicao.save()
    messages.success(request, 'Atribuição reativada com sucesso.')
    return redirect('atribuicao_lista')


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
    initial = {'ativo': True}


class DiretorTurmaUpdateView(AdministradorRequeridoMixin, UpdateView):
    model = DiretorTurma
    form_class = DiretorTurmaForm
    template_name = 'professores/diretor_turma_form.html'
    success_url = reverse_lazy('diretor_turma_lista')


class DiretorTurmaDetailView(AdministradorRequeridoMixin, DetailView):
    model = DiretorTurma
    template_name = 'professores/diretor_turma_detalhe.html'
    context_object_name = 'diretor'


class DiretorTurmaDeleteView(AdministradorRequeridoMixin, DeleteView):
    model = DiretorTurma
    template_name = 'professores/diretor_turma_excluir.html'
    context_object_name = 'diretor'
    success_url = reverse_lazy('diretor_turma_lista')