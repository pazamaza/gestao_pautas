from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.decoracors import (
    aluno_requerido,
    chefe_secretaria_requerido,
)
from accounts.utils import (
    eh_subdiretor_pedagogico,
    eh_diretor_geral,
    eh_chefe_secretaria,
    eh_admin_ou_professor,
)
from alunos.forms import DadosCertificadoForm
from alunos.models import Matricula
from notificacoes.models import Notificacao
from notificacoes.services import notificar
from professores.models import DiretorTurma

from .forms import (
    AutorizarPedidoForm,
    ComprovativoPagamentoForm,
    ObservacoesValidacaoForm,
    SolicitarDocumentoForm,
)
from .models import PedidoDocumento, ResultadoDisciplina
from .services.pdf import exportar_boletim_pdf, exportar_certificado_pdf, exportar_declaracao_pdf


def _usuarios_administradores():
    return User.objects.filter(
        Q(groups__name='Sub-diretor Pedagógico') | Q(is_superuser=True)
    ).distinct()


def _usuarios_diretor_geral():
    return User.objects.filter(
        Q(groups__name='Diretor Geral do Complexo') | Q(is_superuser=True)
    ).distinct()


def _usuarios_secretaria():
    return User.objects.filter(groups__name='Chefe de Secretaria').distinct()


def _aprovador_boletim(aluno, ano_letivo):
    diretor = DiretorTurma.objects.filter(
        turma=aluno.turma, ano_letivo=ano_letivo, ativo=True
    ).select_related('professor__user').first()
    return diretor.professor.user if diretor else None


def _autenticadores_pedido(pedido):
    # Quem autentica o documento já emitido pela Secretaria, consoante o
    # tipo: Certificado -> Diretor Geral; Declaração -> Sub-diretor
    # Pedagógico; Boletim -> Diretor de Turma do aluno (ou Sub-diretor, na
    # ausência de um).
    if pedido.tipo == PedidoDocumento.TIPO_CERTIFICADO:
        return _usuarios_diretor_geral()
    if pedido.tipo == PedidoDocumento.TIPO_DECLARACAO:
        return _usuarios_administradores()
    aprovador = _aprovador_boletim(pedido.aluno, pedido.ano_letivo)
    if aprovador:
        return [aprovador]
    return _usuarios_administradores()


def _pode_autorizar_pedido(user):
    # Decisão de autorizar/recusar o pedido (e emitir a nota de pagamento)
    # está centralizada na Secretaria, para todos os tipos de documento —
    # quem valida o mérito do conteúdo é só chamado mais tarde, para
    # autenticar o documento já emitido (ver _pode_autenticar_pedido).
    return eh_chefe_secretaria(user)


def _pode_autenticar_pedido(user, pedido):
    if pedido.tipo == PedidoDocumento.TIPO_CERTIFICADO:
        return eh_diretor_geral(user)
    if pedido.tipo == PedidoDocumento.TIPO_DECLARACAO:
        return eh_subdiretor_pedagogico(user)
    # TIPO_BOLETIM: autentica o Sub-diretor Pedagógico (supervisão) ou o
    # Diretor de Turma do aluno.
    if eh_subdiretor_pedagogico(user):
        return True
    return DiretorTurma.objects.filter(
        professor__user=user, turma=pedido.aluno.turma, ano_letivo=pedido.ano_letivo, ativo=True
    ).exists()


def _pode_ver_pedido(user, pedido):
    if eh_subdiretor_pedagogico(user) or eh_diretor_geral(user) or eh_chefe_secretaria(user):
        return True
    if pedido.aluno.user_id == user.id:
        return True
    return _pode_autenticar_pedido(user, pedido)


def _pode_gerir_fila_documentos(user):
    # Quem vê a fila de pedidos pendentes de autorização: Secretaria (só
    # quem decide, desde que a decisão de mérito passou a ser dela) e
    # Sub-diretor Pedagógico/Diretor Geral (supervisão).
    return eh_subdiretor_pedagogico(user) or eh_diretor_geral(user) or eh_chefe_secretaria(user)


def _pode_ver_fila_autenticacao(user):
    # Quem vê a fila de documentos emitidos a aguardar autenticação:
    # Sub-diretor Pedagógico e Diretor Geral (supervisão) e professores (só
    # os seus, como Diretores de Turma — filtrado dentro da própria view).
    return eh_admin_ou_professor(user) or eh_diretor_geral(user)


def _gestao_documentos_requerida(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not _pode_gerir_fila_documentos(request.user):
            return render(request, 'dashboards/sem_permissao.html', status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def _autenticacao_requerida(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not _pode_ver_fila_autenticacao(request.user):
            return render(request, 'dashboards/sem_permissao.html', status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


@aluno_requerido
def solicitar_documento(request):
    aluno = getattr(request.user, 'aluno', None)
    if not aluno:
        return render(request, 'dashboards/sem_permissao.html', status=403)

    if request.method == 'POST':
        form = SolicitarDocumentoForm(request.POST)
        if form.is_valid():
            if (
                form.cleaned_data['tipo'] == PedidoDocumento.TIPO_CERTIFICADO
                and not aluno.dados_certificado_completos()
            ):
                messages.warning(
                    request,
                    'Antes de solicitar o Certificado, complete os seus dados pessoais '
                    'e anexe a fotocópia do B.I.',
                )
                return redirect('completar_dados_certificado')

            pedido = PedidoDocumento.objects.create(
                aluno=aluno,
                tipo=form.cleaned_data['tipo'],
                ano_letivo=form.cleaned_data['ano_letivo'],
            )
            notificar(
                _usuarios_secretaria(),
                titulo=f'Novo pedido de {pedido.get_tipo_display()}',
                mensagem=(
                    f'{aluno.nome} solicitou {pedido.get_tipo_display()} '
                    f'do ano letivo {pedido.ano_letivo}.'
                ),
                link_url=reverse('pedidos_documentos_pendentes'),
            )
            messages.success(request, f'Pedido de {pedido.get_tipo_display()} submetido com sucesso.')
            return redirect('meus_pedidos_documentos')
    else:
        form = SolicitarDocumentoForm()

    return render(request, 'pautas/solicitar_documento.html', {'form': form})


@aluno_requerido
def completar_dados_certificado(request):
    aluno = getattr(request.user, 'aluno', None)
    if not aluno:
        return render(request, 'dashboards/sem_permissao.html', status=403)

    if request.method == 'POST':
        form = DadosCertificadoForm(request.POST, request.FILES, instance=aluno)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dados guardados com sucesso.')
            return redirect('meus_pedidos_documentos')
    else:
        form = DadosCertificadoForm(instance=aluno)

    return render(request, 'pautas/completar_dados_certificado.html', {'form': form, 'aluno': aluno})


@aluno_requerido
def meus_pedidos_documentos(request):
    aluno = getattr(request.user, 'aluno', None)
    pedidos = (
        PedidoDocumento.objects.filter(aluno=aluno).select_related('ano_letivo')
        if aluno else PedidoDocumento.objects.none()
    )
    return render(request, 'pautas/meus_pedidos.html', {'pedidos': pedidos})


@aluno_requerido
def pedido_carregar_comprovativo(request, pk):
    aluno = getattr(request.user, 'aluno', None)
    pedido = get_object_or_404(PedidoDocumento, pk=pk, aluno=aluno)

    if pedido.status != PedidoDocumento.STATUS_AUTORIZADO:
        messages.error(request, 'Este pedido não está a aguardar comprovativo de pagamento.')
        return redirect('meus_pedidos_documentos')

    if request.method == 'POST':
        form = ComprovativoPagamentoForm(request.POST, request.FILES)
        if form.is_valid():
            pedido.submeter_pagamento(form.cleaned_data['comprovativo_pagamento'])
            notificar(
                _usuarios_secretaria(),
                titulo='Comprovativo de pagamento submetido',
                mensagem=(
                    f'{aluno.nome} submeteu o comprovativo de pagamento do pedido de '
                    f'{pedido.get_tipo_display()}.'
                ),
                link_url=reverse('pedidos_pagamento'),
            )
            messages.success(request, 'Comprovativo submetido. Aguarde a confirmação do pagamento.')
            return redirect('meus_pedidos_documentos')
    else:
        form = ComprovativoPagamentoForm()

    return render(request, 'pautas/carregar_comprovativo.html', {'form': form, 'pedido': pedido})


@_gestao_documentos_requerida
def pedidos_documentos_pendentes(request):
    pedidos = PedidoDocumento.objects.filter(
        status=PedidoDocumento.STATUS_PENDENTE
    ).select_related('aluno', 'aluno__turma', 'ano_letivo')

    user = request.user
    for pedido in pedidos:
        pedido.pode_autorizar = _pode_autorizar_pedido(user)

    return render(request, 'pautas/pedidos_pendentes.html', {'pedidos': pedidos})


@_gestao_documentos_requerida
def pedido_autorizar(request, pk):
    pedido = get_object_or_404(
        PedidoDocumento.objects.select_related('aluno', 'aluno__turma', 'ano_letivo'), pk=pk
    )

    if not _pode_autorizar_pedido(request.user):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    if pedido.status != PedidoDocumento.STATUS_PENDENTE:
        messages.error(request, 'Este pedido já foi decidido.')
        return redirect('pedidos_documentos_pendentes')

    if request.method != 'POST':
        return redirect('pedidos_documentos_pendentes')

    form = AutorizarPedidoForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Indique a forma de pagamento para autorizar o pedido.')
        return redirect('pedidos_documentos_pendentes')

    forma_pagamento = form.cleaned_data['forma_pagamento']
    pedido.autorizar(request.user, forma_pagamento)
    notificar(
        [pedido.aluno.user],
        titulo=f'Pedido de {pedido.get_tipo_display()} autorizado',
        mensagem=(
            f'O seu pedido de {pedido.get_tipo_display()} foi autorizado. Forma de pagamento: '
            f'{forma_pagamento}. Efetue o pagamento e carregue o comprovativo para prosseguir.'
        ),
        link_url=reverse('meus_pedidos_documentos'),
    )
    messages.success(request, 'Pedido autorizado; aluno notificado com a forma de pagamento.')
    return redirect('pedidos_documentos_pendentes')


@_gestao_documentos_requerida
def pedido_recusar(request, pk):
    pedido = get_object_or_404(
        PedidoDocumento.objects.select_related('aluno', 'aluno__turma', 'ano_letivo'), pk=pk
    )

    if not _pode_autorizar_pedido(request.user):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    if pedido.status != PedidoDocumento.STATUS_PENDENTE:
        messages.error(request, 'Este pedido já foi decidido.')
        return redirect('pedidos_documentos_pendentes')

    if request.method != 'POST':
        return redirect('pedidos_documentos_pendentes')

    form = ObservacoesValidacaoForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Indique o motivo da recusa.')
        return redirect('pedidos_documentos_pendentes')

    motivo = form.cleaned_data['observacoes_validacao']
    pedido.recusar(request.user, motivo)
    notificar(
        [pedido.aluno.user],
        titulo=f'Pedido de {pedido.get_tipo_display()} recusado',
        mensagem=f'O seu pedido de {pedido.get_tipo_display()} foi recusado. Motivo: {motivo}',
        nivel=Notificacao.NIVEL_AVISO,
        link_url=reverse('meus_pedidos_documentos'),
    )
    messages.success(request, 'Pedido recusado; aluno notificado.')
    return redirect('pedidos_documentos_pendentes')


@chefe_secretaria_requerido
def pedidos_pagamento(request):
    pedidos = PedidoDocumento.objects.filter(
        status=PedidoDocumento.STATUS_PAGAMENTO_SUBMETIDO
    ).select_related('aluno', 'ano_letivo')
    a_emitir = PedidoDocumento.objects.filter(
        status=PedidoDocumento.STATUS_PAGAMENTO_CONFIRMADO
    ).select_related('aluno', 'ano_letivo')
    a_notificar = PedidoDocumento.objects.filter(
        status=PedidoDocumento.STATUS_AUTENTICADO
    ).select_related('aluno', 'ano_letivo')
    prontos = PedidoDocumento.objects.filter(
        status=PedidoDocumento.STATUS_PRONTO
    ).select_related('aluno', 'ano_letivo')
    return render(request, 'pautas/pedidos_pagamento.html', {
        'pedidos': pedidos,
        'a_emitir': a_emitir,
        'a_notificar': a_notificar,
        'prontos': prontos,
    })


@chefe_secretaria_requerido
def pedido_confirmar_pagamento(request, pk):
    pedido = get_object_or_404(PedidoDocumento.objects.select_related('aluno'), pk=pk)
    if pedido.status != PedidoDocumento.STATUS_PAGAMENTO_SUBMETIDO:
        messages.error(request, 'Este pedido não tem comprovativo submetido para confirmar.')
        return redirect('pedidos_pagamento')
    pedido.confirmar_pagamento(request.user)
    # Ainda não notifica o aluno — o documento só está pronto depois de
    # emitido pela Secretaria e autenticado por quem de direito (ver
    # pedido_emitir / pedido_autenticar / pedido_notificar_aluno).
    messages.success(request, 'Pagamento confirmado; pedido aguarda emissão do documento.')
    return redirect('pedidos_pagamento')


@chefe_secretaria_requerido
def pedido_emitir(request, pk):
    pedido = get_object_or_404(
        PedidoDocumento.objects.select_related('aluno', 'aluno__turma', 'ano_letivo'), pk=pk
    )
    if pedido.status != PedidoDocumento.STATUS_PAGAMENTO_CONFIRMADO:
        messages.error(request, 'Este pedido não está pronto para emissão.')
        return redirect('pedidos_pagamento')

    pedido.emitir(request.user)
    notificar(
        _autenticadores_pedido(pedido),
        titulo=f'Documento de {pedido.get_tipo_display()} aguarda autenticação',
        mensagem=(
            f'O documento de {pedido.get_tipo_display()} de {pedido.aluno.nome} foi emitido '
            'pela Secretaria e aguarda a sua autenticação.'
        ),
        link_url=reverse('pedidos_autenticacao'),
    )
    messages.success(request, 'Documento emitido; autenticação solicitada.')
    return redirect('pedidos_pagamento')


@_autenticacao_requerida
def pedidos_autenticacao(request):
    pedidos = PedidoDocumento.objects.filter(
        status=PedidoDocumento.STATUS_EMITIDO
    ).select_related('aluno', 'aluno__turma', 'ano_letivo')

    user = request.user
    if not (eh_subdiretor_pedagogico(user) or eh_diretor_geral(user)):
        # Professor "comum": só os boletins das turmas onde é Diretor de Turma.
        turmas_dirigidas = DiretorTurma.objects.filter(
            professor__user=user, ativo=True
        ).values_list('turma_id', flat=True)
        pedidos = pedidos.filter(tipo=PedidoDocumento.TIPO_BOLETIM, aluno__turma_id__in=turmas_dirigidas)

    for pedido in pedidos:
        pedido.pode_autenticar = _pode_autenticar_pedido(user, pedido)

    return render(request, 'pautas/pedidos_autenticacao.html', {'pedidos': pedidos})


@login_required
def pedido_autenticar(request, pk):
    pedido = get_object_or_404(
        PedidoDocumento.objects.select_related('aluno', 'aluno__turma', 'ano_letivo'), pk=pk
    )

    if not _pode_autenticar_pedido(request.user, pedido):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    if pedido.status != PedidoDocumento.STATUS_EMITIDO:
        messages.error(request, 'Este documento ainda não foi emitido pela Secretaria.')
        return redirect('pedidos_autenticacao')

    pedido.autenticar(request.user)
    notificar(
        _usuarios_secretaria(),
        titulo=f'Documento de {pedido.get_tipo_display()} autenticado',
        mensagem=(
            f'O documento de {pedido.get_tipo_display()} de {pedido.aluno.nome} foi autenticado. '
            'Pode notificar o aluno para levantamento.'
        ),
        link_url=reverse('pedidos_pagamento'),
    )
    messages.success(request, 'Documento autenticado; Secretaria notificada.')
    return redirect('pedidos_autenticacao')


@chefe_secretaria_requerido
def pedido_notificar_aluno(request, pk):
    pedido = get_object_or_404(PedidoDocumento.objects.select_related('aluno'), pk=pk)
    if pedido.status != PedidoDocumento.STATUS_AUTENTICADO:
        messages.error(request, 'Este pedido ainda não foi autenticado.')
        return redirect('pedidos_pagamento')

    pedido.marcar_pronto()
    notificar(
        [pedido.aluno.user],
        titulo=f'{pedido.get_tipo_display()} pronto para levantamento',
        mensagem=(
            f'O seu pedido de {pedido.get_tipo_display()} foi autenticado e está pronto. '
            'Pode levantar o documento na secretaria.'
        ),
        link_url=reverse('meus_pedidos_documentos'),
    )
    messages.success(request, 'Aluno notificado para levantamento.')
    return redirect('pedidos_pagamento')


@chefe_secretaria_requerido
def pedido_rejeitar_pagamento(request, pk):
    pedido = get_object_or_404(PedidoDocumento.objects.select_related('aluno'), pk=pk)
    if pedido.status != PedidoDocumento.STATUS_PAGAMENTO_SUBMETIDO:
        messages.error(request, 'Este pedido não tem comprovativo submetido para rejeitar.')
        return redirect('pedidos_pagamento')
    pedido.rejeitar_pagamento(request.user)
    notificar(
        [pedido.aluno.user],
        titulo='Comprovativo de pagamento rejeitado',
        mensagem=(
            f'O comprovativo submetido para o pedido de {pedido.get_tipo_display()} não foi '
            'validado. Por favor, submeta novamente.'
        ),
        nivel=Notificacao.NIVEL_AVISO,
        link_url=reverse('meus_pedidos_documentos'),
    )
    messages.warning(request, 'Comprovativo rejeitado; aluno notificado.')
    return redirect('pedidos_pagamento')


@chefe_secretaria_requerido
def pedido_marcar_levantado(request, pk):
    pedido = get_object_or_404(PedidoDocumento, pk=pk)
    if pedido.status != PedidoDocumento.STATUS_PRONTO:
        messages.error(request, 'Este pedido ainda não está pronto para levantamento.')
        return redirect('pedidos_pagamento')
    pedido.marcar_levantado()
    messages.success(request, 'Pedido marcado como levantado.')
    return redirect('pedidos_pagamento')


@login_required
def pedido_emitir_pdf(request, pk):
    pedido = get_object_or_404(
        PedidoDocumento.objects.select_related('aluno', 'aluno__turma', 'ano_letivo'), pk=pk
    )

    if not _pode_ver_pedido(request.user, pedido):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    if pedido.aluno.user_id == request.user.id:
        # O aluno só descarrega depois do documento estar autenticado e a
        # Secretaria o ter chamado para levantamento.
        estados_permitidos = (PedidoDocumento.STATUS_PRONTO, PedidoDocumento.STATUS_LEVANTADO)
    else:
        # Secretaria/autenticador podem pré-visualizar assim que o
        # documento é emitido, antes mesmo da autenticação.
        estados_permitidos = (
            PedidoDocumento.STATUS_EMITIDO,
            PedidoDocumento.STATUS_AUTENTICADO,
            PedidoDocumento.STATUS_PRONTO,
            PedidoDocumento.STATUS_LEVANTADO,
        )

    if pedido.status not in estados_permitidos:
        messages.error(request, 'Este documento ainda não está pronto para emissão.')
        return redirect('meus_pedidos_documentos')

    resultados = ResultadoDisciplina.objects.filter(
        aluno=pedido.aluno, ano_letivo=pedido.ano_letivo, status=ResultadoDisciplina.STATUS_VALIDADA,
    ).select_related('disciplina').order_by('disciplina__nome')

    if pedido.tipo == PedidoDocumento.TIPO_BOLETIM:
        arquivo = exportar_boletim_pdf(pedido.aluno, pedido.ano_letivo, resultados)
        nome = f'boletim_{pedido.aluno.numero_processo}_{pedido.ano_letivo_id}.pdf'
    elif pedido.tipo == PedidoDocumento.TIPO_DECLARACAO:
        arquivo = exportar_declaracao_pdf(pedido.aluno, pedido.ano_letivo, resultados)
        nome = f'declaracao_{pedido.aluno.numero_processo}_{pedido.ano_letivo_id}.pdf'
    else:
        matricula = Matricula.objects.filter(
            aluno=pedido.aluno, ano_letivo=pedido.ano_letivo
        ).select_related('turma__classe').first()
        turma = matricula.turma if matricula else pedido.aluno.turma
        arquivo = exportar_certificado_pdf(pedido.aluno, turma, pedido.ano_letivo, resultados)
        nome = f'certificado_{pedido.aluno.numero_processo}_{pedido.ano_letivo_id}.pdf'

    return FileResponse(
        arquivo, as_attachment=True, filename=nome, content_type='application/pdf'
    )
