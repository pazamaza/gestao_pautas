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

from .forms import ComprovativoPagamentoForm, ObservacoesValidacaoForm, SolicitarDocumentoForm
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


def _decisores_pedido(pedido):
    if pedido.tipo == PedidoDocumento.TIPO_CERTIFICADO:
        return _usuarios_diretor_geral()
    if pedido.tipo == PedidoDocumento.TIPO_DECLARACAO:
        return _usuarios_administradores()
    aprovador = _aprovador_boletim(pedido.aluno, pedido.ano_letivo)
    if aprovador:
        return [aprovador]
    return _usuarios_administradores()


def _destinatarios_pedido(pedido):
    # A Secretaria é o ponto único de entrada e acompanha todos os pedidos;
    # quem efetivamente decide (Diretor Geral/Sub-diretor/Diretor de Turma,
    # conforme o tipo) é notificado em simultâneo, para não perder o tempo
    # de resposta que já existia antes desta reorganização.
    destinatarios = set(_decisores_pedido(pedido))
    destinatarios |= set(_usuarios_secretaria())
    return destinatarios


def _pode_decidir_pedido(user, pedido):
    if pedido.tipo == PedidoDocumento.TIPO_CERTIFICADO:
        return eh_diretor_geral(user)
    if pedido.tipo == PedidoDocumento.TIPO_DECLARACAO:
        return eh_subdiretor_pedagogico(user)
    # TIPO_BOLETIM: decisão de mérito continua com o Sub-diretor Pedagógico
    # (supervisão) ou o Diretor de Turma da turma do aluno. A centralização
    # completa na Secretaria (Secretaria decide, Diretor de Turma só
    # autentica) fica para uma fase seguinte.
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
    return _pode_decidir_pedido(user, pedido)


def _pode_gerir_fila_documentos(user):
    # Quem vê a fila de pedidos pendentes: Secretaria (ponto único de
    # entrada, vê tudo), Sub-diretor Pedagógico e Diretor Geral (autenticam
    # declaração/certificado, respetivamente) e professores (só os seus
    # boletins, filtrados dentro da própria view).
    return eh_admin_ou_professor(user) or eh_diretor_geral(user) or eh_chefe_secretaria(user)


def _gestao_documentos_requerida(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not _pode_gerir_fila_documentos(request.user):
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
                _destinatarios_pedido(pedido),
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
                _usuarios_administradores(),
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
    if not (eh_subdiretor_pedagogico(user) or eh_diretor_geral(user) or eh_chefe_secretaria(user)):
        # Professor "comum": só os boletins das turmas onde é Diretor de Turma.
        turmas_dirigidas = DiretorTurma.objects.filter(
            professor__user=user, ativo=True
        ).values_list('turma_id', flat=True)
        pedidos = pedidos.filter(tipo=PedidoDocumento.TIPO_BOLETIM, aluno__turma_id__in=turmas_dirigidas)
    # Secretaria, Sub-diretor e Diretor Geral são o ponto único de entrada:
    # veem a fila completa, de todos os tipos, mesmo os que não decidem —
    # a lista/template só ativa os botões de decisão quando aplicável.

    for pedido in pedidos:
        pedido.pode_decidir = _pode_decidir_pedido(user, pedido)

    return render(request, 'pautas/pedidos_pendentes.html', {'pedidos': pedidos})


@_gestao_documentos_requerida
def pedido_autorizar(request, pk):
    pedido = get_object_or_404(
        PedidoDocumento.objects.select_related('aluno', 'aluno__turma', 'ano_letivo'), pk=pk
    )

    if not _pode_decidir_pedido(request.user, pedido):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    if pedido.status != PedidoDocumento.STATUS_PENDENTE:
        messages.error(request, 'Este pedido já foi decidido.')
        return redirect('pedidos_documentos_pendentes')

    pedido.autorizar(request.user)
    notificar(
        [pedido.aluno.user],
        titulo=f'Pedido de {pedido.get_tipo_display()} autorizado',
        mensagem=(
            f'O seu pedido de {pedido.get_tipo_display()} foi autorizado. Efetue o pagamento '
            'através do GPS (Ruper) e carregue o comprovativo para prosseguir.'
        ),
        link_url=reverse('meus_pedidos_documentos'),
    )
    messages.success(request, 'Pedido autorizado; aluno notificado.')
    return redirect('pedidos_documentos_pendentes')


@_gestao_documentos_requerida
def pedido_recusar(request, pk):
    pedido = get_object_or_404(
        PedidoDocumento.objects.select_related('aluno', 'aluno__turma', 'ano_letivo'), pk=pk
    )

    if not _pode_decidir_pedido(request.user, pedido):
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
    prontos = PedidoDocumento.objects.filter(
        status=PedidoDocumento.STATUS_PRONTO
    ).select_related('aluno', 'ano_letivo')
    return render(request, 'pautas/pedidos_pagamento.html', {'pedidos': pedidos, 'prontos': prontos})


@chefe_secretaria_requerido
def pedido_confirmar_pagamento(request, pk):
    pedido = get_object_or_404(PedidoDocumento.objects.select_related('aluno'), pk=pk)
    if pedido.status != PedidoDocumento.STATUS_PAGAMENTO_SUBMETIDO:
        messages.error(request, 'Este pedido não tem comprovativo submetido para confirmar.')
        return redirect('pedidos_pagamento')
    pedido.confirmar_pagamento(request.user)
    notificar(
        [pedido.aluno.user],
        titulo=f'{pedido.get_tipo_display()} pronto para levantamento',
        mensagem=(
            f'O pagamento do seu pedido de {pedido.get_tipo_display()} foi confirmado. '
            'Pode levantar o documento na secretaria.'
        ),
        link_url=reverse('meus_pedidos_documentos'),
    )
    messages.success(request, 'Pagamento confirmado; aluno notificado para levantamento.')
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

    if pedido.status not in (PedidoDocumento.STATUS_PRONTO, PedidoDocumento.STATUS_LEVANTADO):
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
