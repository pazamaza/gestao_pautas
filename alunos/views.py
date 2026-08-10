from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import ProtectedError, Q
from django.urls import reverse, reverse_lazy
from django.views.generic import (ListView, CreateView,
    UpdateView, DeleteView, DetailView)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from .models import ( Aluno, Encarregado, Reclamacao)
from .forms import (
    AlunoForm, EncarregadoCadastroForm, EncarregadoEdicaoForm,
    ReclamacaoForm, EncaminharReclamacaoForm, ResolverReclamacaoForm,
)
from django.contrib.auth.models import Group, User
from django.shortcuts import (render, redirect,
    get_object_or_404)
from django.views import View
from accounts.utils import (
    eh_subdiretor_pedagogico,
    eh_professor,
    eh_coordenador_pais_encarregados,
    eh_diretor_geral,
    eh_chefe_secretaria,
)
from accounts.mixins import (
    SubdiretorPedagogicoRequeridoMixin,
    AdminOuProfessorRequeridoMixin,
    AcessoRestritoMixin,
    CoordenadorPaisRequeridoMixin,
)
from notificacoes.services import notificar
from professores.models import AtribuicaoDocente, DiretorTurma
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


def _usuarios_coordenadores_pais():
    return User.objects.filter(groups__name='Coordenador de Pais e Encarregados de Educação').distinct()


def _usuarios_secretaria():
    return User.objects.filter(groups__name='Chefe de Secretaria').distinct()


def _usuarios_diretor_geral():
    return User.objects.filter(
        Q(groups__name='Diretor Geral do Complexo') | Q(is_superuser=True)
    ).distinct()


def _usuarios_subdiretor_pedagogico():
    return User.objects.filter(
        Q(groups__name='Sub-diretor Pedagógico') | Q(is_superuser=True)
    ).distinct()


def _diretor_turma_do_aluno(aluno):
    if not aluno:
        return None
    turma = aluno.turma
    diretor = DiretorTurma.objects.filter(
        turma=turma, ano_letivo=turma.ano_letivo, ativo=True
    ).select_related('professor__user').first()
    return diretor.professor.user if diretor else None


def _usuarios_do_destino(destino, reclamacao):
    if destino == Reclamacao.ENCAMINHAMENTO_SECRETARIA:
        return _usuarios_secretaria()
    if destino == Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL:
        return _usuarios_diretor_geral()
    if destino == Reclamacao.ENCAMINHAMENTO_SUBDIRETOR_PEDAGOGICO:
        return _usuarios_subdiretor_pedagogico()
    if destino == Reclamacao.ENCAMINHAMENTO_DIRETOR_TURMA:
        diretor_user = _diretor_turma_do_aluno(reclamacao.aluno)
        return [diretor_user] if diretor_user else []
    return []


def _pode_ver_reclamacoes(user):
    if eh_coordenador_pais_encarregados(user) or eh_chefe_secretaria(user) or eh_diretor_geral(user) \
            or eh_subdiretor_pedagogico(user):
        return True
    return DiretorTurma.objects.filter(professor__user=user, ativo=True).exists()


def _reclamacoes_visiveis(user):
    if eh_coordenador_pais_encarregados(user):
        return Reclamacao.objects.all()
    if eh_chefe_secretaria(user):
        return Reclamacao.objects.exclude(estado=Reclamacao.ESTADO_ABERTA)
    if eh_diretor_geral(user):
        return Reclamacao.objects.filter(encaminhado_para__in=[
            Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL,
            Reclamacao.ENCAMINHAMENTO_SUBDIRETOR_PEDAGOGICO,
            Reclamacao.ENCAMINHAMENTO_DIRETOR_TURMA,
        ])
    if eh_subdiretor_pedagogico(user):
        return Reclamacao.objects.filter(encaminhado_para=Reclamacao.ENCAMINHAMENTO_SUBDIRETOR_PEDAGOGICO)
    turmas_dirigidas = DiretorTurma.objects.filter(
        professor__user=user, ativo=True
    ).values_list('turma_id', flat=True)
    return Reclamacao.objects.filter(
        encaminhado_para=Reclamacao.ENCAMINHAMENTO_DIRETOR_TURMA, aluno__turma_id__in=turmas_dirigidas
    )


def _destinos_possiveis(user, reclamacao):
    """Para onde o utilizador atual pode encaminhar esta reclamação,
    consoante o ponto da cadeia em que ela está agora."""
    if reclamacao.estado == Reclamacao.ESTADO_ABERTA:
        if eh_coordenador_pais_encarregados(user):
            return [(Reclamacao.ENCAMINHAMENTO_SECRETARIA, 'Secretaria')]
        return []
    if reclamacao.encaminhado_para == Reclamacao.ENCAMINHAMENTO_SECRETARIA:
        if eh_chefe_secretaria(user):
            return [(Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL, 'Diretor Geral')]
        return []
    if reclamacao.encaminhado_para == Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL:
        if not eh_diretor_geral(user):
            return []
        opcoes = [
            (Reclamacao.ENCAMINHAMENTO_SUBDIRETOR_PEDAGOGICO, 'Sub-diretor Pedagógico (assunto de notas/pautas)'),
        ]
        if reclamacao.aluno:
            opcoes.append(
                (Reclamacao.ENCAMINHAMENTO_DIRETOR_TURMA, 'Diretor de Turma (assunto de faltas/justificações)')
            )
        return opcoes
    return []


def _pode_resolver_reclamacao(user, reclamacao):
    if reclamacao.encaminhado_para == Reclamacao.ENCAMINHAMENTO_SUBDIRETOR_PEDAGOGICO:
        return eh_subdiretor_pedagogico(user)
    if reclamacao.encaminhado_para == Reclamacao.ENCAMINHAMENTO_DIRETOR_TURMA:
        if not reclamacao.aluno:
            return False
        turma = reclamacao.aluno.turma
        return DiretorTurma.objects.filter(
            professor__user=user, turma=turma, ano_letivo=turma.ano_letivo, ativo=True
        ).exists()
    if reclamacao.encaminhado_para == Reclamacao.ENCAMINHAMENTO_DIRETOR_GERAL:
        # Assuntos que não são nem de notas/pautas nem de faltas ficam
        # com o próprio Diretor Geral.
        return eh_diretor_geral(user)
    return False


class ReclamacaoAcessoMixin(AcessoRestritoMixin):
    def test_func(self):
        return _pode_ver_reclamacoes(self.request.user)


class ReclamacaoListView(ReclamacaoAcessoMixin, ListView):
    model = Reclamacao
    template_name = 'alunos/reclamacao_lista.html'
    context_object_name = 'reclamacoes'

    def get_queryset(self):
        return _reclamacoes_visiveis(self.request.user).select_related(
            'encarregado__user', 'aluno', 'registada_por'
        )


class ReclamacaoCreateView(CoordenadorPaisRequeridoMixin, CreateView):
    model = Reclamacao
    form_class = ReclamacaoForm
    template_name = 'alunos/reclamacao_form.html'
    success_url = reverse_lazy('reclamacao_lista')

    def form_valid(self, form):
        form.instance.registada_por = self.request.user
        messages.success(self.request, 'Reclamação registada com sucesso.')
        return super().form_valid(form)


class ReclamacaoDetailView(ReclamacaoAcessoMixin, DetailView):
    model = Reclamacao
    template_name = 'alunos/reclamacao_detalhe.html'
    context_object_name = 'reclamacao'

    def get_queryset(self):
        return _reclamacoes_visiveis(self.request.user)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        destinos = _destinos_possiveis(self.request.user, self.object)
        contexto.update({
            'form_encaminhar': EncaminharReclamacaoForm(destinos=destinos),
            'form_resolver': ResolverReclamacaoForm(),
            'pode_encaminhar': bool(destinos),
            'pode_resolver': _pode_resolver_reclamacao(self.request.user, self.object),
        })
        return contexto


@login_required
def reclamacao_encaminhar(request, pk):
    reclamacao = get_object_or_404(_reclamacoes_visiveis(request.user), pk=pk)
    destinos = _destinos_possiveis(request.user, reclamacao)
    destinos_validos = {valor for valor, _ in destinos}
    if not destinos_validos:
        return render(request, 'dashboards/sem_permissao.html', status=403)

    if request.method == 'POST':
        form = EncaminharReclamacaoForm(request.POST, destinos=destinos)
        if form.is_valid() and form.cleaned_data['encaminhado_para'] in destinos_validos:
            destino = form.cleaned_data['encaminhado_para']
            reclamacao.encaminhar(destino)
            notificar(
                _usuarios_do_destino(destino, reclamacao),
                titulo='Reclamação encaminhada para si',
                mensagem=f'Reclamação de {reclamacao.encarregado} encaminhada para decisão.',
                link_url=reverse('reclamacao_detalhe', args=[reclamacao.pk]),
            )
            messages.success(request, 'Reclamação encaminhada.')
    return redirect('reclamacao_detalhe', pk=pk)


@login_required
def reclamacao_resolver(request, pk):
    reclamacao = get_object_or_404(_reclamacoes_visiveis(request.user), pk=pk)
    if not _pode_resolver_reclamacao(request.user, reclamacao):
        return render(request, 'dashboards/sem_permissao.html', status=403)
    if request.method == 'POST':
        form = ResolverReclamacaoForm(request.POST)
        if form.is_valid():
            reclamacao.resolver(form.cleaned_data['observacoes_resolucao'])
            notificar(
                _usuarios_coordenadores_pais(),
                titulo='Reclamação resolvida',
                mensagem=(
                    f'A reclamação de {reclamacao.encarregado} foi resolvida: '
                    f'{form.cleaned_data["observacoes_resolucao"]}'
                ),
                link_url=reverse('reclamacao_detalhe', args=[reclamacao.pk]),
            )
            notificar(
                [reclamacao.encarregado.user],
                titulo='A sua reclamação foi resolvida',
                mensagem=form.cleaned_data['observacoes_resolucao'],
                link_url=reverse('reclamacao_detalhe', args=[reclamacao.pk]),
            )
            messages.success(request, 'Reclamação marcada como resolvida.')
    return redirect('reclamacao_detalhe', pk=pk)

