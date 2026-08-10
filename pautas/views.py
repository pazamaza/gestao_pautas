import statistics
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.decoracors import (
    admin_ou_professor_requerido,
    subdiretor_pedagogico_requerido,
    aluno_requerido,
    encarregado_requerido,
    professor_requerido,
)
from accounts.mixins import (
    AdminOuProfessorRequeridoMixin,
    ProfessorRequeridoMixin,
    SuperuserRequeridoMixin,
)
from accounts.utils import eh_subdiretor_pedagogico
from alunos.models import Aluno
from disciplinas.models import Disciplina
from professores.models import AtribuicaoDocente, DiretorTurma
from turmas.models import AnoLetivo, PeriodoAcademico, Turma
from notificacoes.services import notificar_erro_pauta

from .forms import (
    AvaliacaoForm,
    ImportarNotasExcelForm,
    LancamentoNotaFormSet,
    NotaForm,
    ObservacoesValidacaoForm,
    ResultadoDisciplinaForm,
)
from .models import Avaliacao, Nota, ResultadoDisciplina, SituacaoAnual
from .services.excel import (
    criar_modelo_excel,
    exportar_mini_pauta_excel,
    exportar_pauta_excel,
    importar_notas_excel,
)
from .services.pdf import exportar_mini_pauta_pdf, exportar_pauta_final_pdf, exportar_pauta_pdf
from .services.periodos import campo_periodo
from .services.resultados import (
    atualizar_resultado_disciplina,
    gerar_resultados_finais,
    montar_mini_pauta_disciplina,
    montar_pauta_final_turma,
    verificar_transicao_aluno,
)


def notas_da_avaliacao(avaliacao):
    return (
        Nota.objects
        .filter(avaliacao=avaliacao)
        .select_related('aluno')
        .order_by('aluno__nome')
    )


def _medias_periodos_anteriores(alunos, atribuicao, periodo):
    """Devolve (medias, campos) com a MT dos trimestres anteriores ao `periodo`
    para a mesma disciplina/turma/ano letivo, para exibir como referência
    ao lançar o 2º/3º trimestre. `medias` é {aluno_id: {'mt1': Decimal, ...}}."""
    campo_atual = campo_periodo(periodo)
    if campo_atual == 'mt2':
        campos = ['mt1']
    elif campo_atual == 'mt3':
        campos = ['mt1', 'mt2']
    else:
        return {}, []

    notas = Nota.objects.filter(
        aluno__in=alunos,
        avaliacao__atribuicao__disciplina=atribuicao.disciplina,
        avaliacao__atribuicao__turma=atribuicao.turma,
        avaliacao__atribuicao__ano_letivo=atribuicao.ano_letivo,
    ).select_related('avaliacao__periodo')

    medias = {}
    for nota in notas:
        campo = campo_periodo(nota.avaliacao.periodo)
        if campo in campos:
            medias.setdefault(nota.aluno_id, {})[campo] = nota.mt

    return medias, campos


def _eh_professor_titular(user, avaliacao):
    return avaliacao.atribuicao.professor.user_id == user.id


def _eh_diretor_da_turma(user, turma, ano_letivo):
    return DiretorTurma.objects.filter(
        turma=turma, ano_letivo=ano_letivo, professor__user=user, ativo=True
    ).exists()


def _pode_ver_avaliacao(user, avaliacao):
    if eh_subdiretor_pedagogico(user) or _eh_professor_titular(user, avaliacao):
        return True
    return _eh_diretor_da_turma(user, avaliacao.atribuicao.turma, avaliacao.atribuicao.ano_letivo)


def _pode_ver_pauta_final(user, turma, ano_letivo):
    if eh_subdiretor_pedagogico(user):
        return True
    return bool(ano_letivo and _eh_diretor_da_turma(user, turma, ano_letivo))


def _gravar_notas_recurso(request, alunos, disciplina, ano_letivo):
    """Grava as NER (Nota de Exame de Recurso) enviadas no POST — um campo
    'ner_<aluno_id>' por aluno, fora de qualquer formset porque vive em
    ResultadoDisciplina, não em Nota. Só aceita para quem já ficou
    "Recurso" (ver ResultadoDisciplina._verificar_resultado_segundo_ano);
    usado tanto em lancamento_notas como na mini-pauta. Devolve
    (gravadas, erros)."""
    resultados_por_aluno = {
        r.aluno_id: r for r in ResultadoDisciplina.objects.filter(
            aluno__in=alunos, disciplina=disciplina, ano_letivo=ano_letivo,
        )
    }
    erros = []
    gravadas = 0
    for aluno in alunos:
        valor_bruto = request.POST.get(f'ner_{aluno.id}', '').strip()
        if not valor_bruto:
            continue
        resultado = resultados_por_aluno.get(aluno.id)
        if not resultado or resultado.resultado != ResultadoDisciplina.RESULTADO_RECURSO:
            erros.append(f'{aluno}: esta disciplina não está em Recurso — NER ignorada.')
            continue
        try:
            valor = Decimal(valor_bruto.replace(',', '.'))
        except InvalidOperation:
            erros.append(f'{aluno}: NER inválida.')
            continue
        if not (0 <= valor <= 20):
            erros.append(f'{aluno}: NER tem de estar entre 0 e 20.')
            continue
        resultado.nota_recurso = valor
        if resultado.status == ResultadoDisciplina.STATUS_VALIDADA:
            # A NER muda o resultado "por baixo" de uma validação já feita
            # antes do recurso — volta a "rascunho" para obrigar a uma nova
            # validação do admin antes de contar como definitivo para o
            # aluno (ver _pautas_validadas_do_aluno, que só mostra
            # status='validada').
            resultado.status = ResultadoDisciplina.STATUS_RASCUNHO
            resultado.validado_por = None
            resultado.validado_em = None
        resultado.save()
        gravadas += 1
    return gravadas, erros


@admin_ou_professor_requerido
def lancamento_notas(request):
    atribuicoes = AtribuicaoDocente.objects.filter(ativo=True).select_related(
        'disciplina', 'turma', 'ano_letivo'
    )
    if not eh_subdiretor_pedagogico(request.user):
        atribuicoes = atribuicoes.filter(professor__user=request.user)
    atribuicoes = atribuicoes.order_by('turma__classe__nome', 'turma__nome', 'disciplina__nome')

    contexto = {'atribuicoes': atribuicoes, 'atribuicao': None, 'periodo': None, 'periodos': []}

    if not atribuicoes.exists():
        messages.warning(request, 'Não existe nenhuma atribuição docente ativa associada a si.')
        return render(request, 'pautas/lancamento_notas.html', contexto)

    atribuicao_id = request.GET.get('atribuicao') or request.POST.get('atribuicao')
    atribuicao = atribuicoes.filter(pk=atribuicao_id).first() if atribuicao_id else None
    atribuicao = atribuicao or atribuicoes.first()
    contexto['atribuicao'] = atribuicao

    periodos = PeriodoAcademico.objects.filter(ano_letivo=atribuicao.ano_letivo).order_by('nome')
    contexto['periodos'] = periodos

    periodo_id = request.GET.get('periodo') or request.POST.get('periodo')
    periodo = periodos.filter(pk=periodo_id).first() if periodo_id else None
    periodo = periodo or periodos.filter(aberto=True).first() or periodos.first()
    contexto['periodo'] = periodo

    if not periodo:
        messages.warning(request, 'Não existe nenhum período académico configurado para este ano letivo.')
        return render(request, 'pautas/lancamento_notas.html', contexto)

    avaliacao, _ = Avaliacao.objects.get_or_create(atribuicao=atribuicao, periodo=periodo)

    if not _pode_ver_avaliacao(request.user, avaliacao):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    pode_editar = eh_subdiretor_pedagogico(request.user) or _eh_professor_titular(request.user, avaliacao)
    periodo_ativo = periodo.periodo_lancamento_ativo()

    alunos = list(
        Aluno.objects.filter(turma=atribuicao.turma, estado=Aluno.ESTADO_ATIVO).order_by('nome')
    )

    eh_terceiro_trimestre_iiano = bool(
        periodo and campo_periodo(periodo) == 'mt3' and atribuicao.turma.eh_segundo_ano()
    )

    notas_existentes = {
        nota.aluno_id: nota
        for nota in Nota.objects.filter(avaliacao=avaliacao, aluno__in=alunos)
    }

    if request.method == 'POST':
        if not pode_editar:
            return render(request, 'dashboards/sem_permissao.html', status=403)
        if not periodo_ativo:
            messages.error(request, 'Fora do período de lançamento de notas para este trimestre.')
            return redirect(f"{reverse('lancamento_notas')}?atribuicao={atribuicao.id}&periodo={periodo.id}")

        formset = LancamentoNotaFormSet(request.POST)
        if formset.is_valid():
            erros = []
            gravados = 0
            for form in formset:
                aluno_id = form.cleaned_data['aluno_id']
                mac = form.cleaned_data.get('mac')
                npt = form.cleaned_data.get('npt')
                if mac is None or npt is None:
                    continue
                try:
                    nota, _ = Nota.objects.update_or_create(
                        avaliacao=avaliacao, aluno_id=aluno_id,
                        defaults={'mac': mac, 'npt': npt},
                    )
                except ValueError as exc:
                    aluno = next((a for a in alunos if a.id == aluno_id), None)
                    erros.append(f"{aluno}: {exc}" if aluno else str(exc))
                    continue
                atualizar_resultado_disciplina(nota.aluno, atribuicao.disciplina, atribuicao.ano_letivo)
                gravados += 1

            if eh_terceiro_trimestre_iiano:
                # NER (Nota de Exame de Recurso) — só se aplica ao IIº Ano,
                # e só a disciplinas que já ficaram "Recurso" (MFA 7-9, sem
                # veto do gatilho); campos extra no mesmo POST, um por aluno
                # (ner_<id>), fora do formset porque vive em
                # ResultadoDisciplina, não em Nota.
                ner_gravadas, erros_ner = _gravar_notas_recurso(
                    request, alunos, atribuicao.disciplina, atribuicao.ano_letivo
                )
                erros.extend(erros_ner)
                if ner_gravadas:
                    messages.success(request, f'{ner_gravadas} nota(s) de recurso (NER) gravada(s).')

            if gravados:
                messages.success(request, f'{gravados} nota(s) gravada(s) com sucesso.')
            if erros:
                messages.warning(request, 'Não foi possível gravar: ' + '; '.join(erros))

            return redirect(f"{reverse('lancamento_notas')}?atribuicao={atribuicao.id}&periodo={periodo.id}")
    else:
        initial = [
            {
                'aluno_id': aluno.id,
                'mac': notas_existentes[aluno.id].mac if aluno.id in notas_existentes else None,
                'npt': notas_existentes[aluno.id].npt if aluno.id in notas_existentes else None,
            }
            for aluno in alunos
        ]
        formset = LancamentoNotaFormSet(initial=initial)

    medias_anteriores, campos_anteriores = _medias_periodos_anteriores(alunos, atribuicao, periodo)

    resultados_por_aluno = {}
    if eh_terceiro_trimestre_iiano:
        resultados_por_aluno = {
            r.aluno_id: r for r in ResultadoDisciplina.objects.filter(
                aluno__in=alunos, disciplina=atribuicao.disciplina, ano_letivo=atribuicao.ano_letivo,
            )
        }

    linhas = []
    for aluno, form in zip(alunos, formset):
        nota_gravada = aluno.id in notas_existentes
        if nota_gravada:
            # MAC/NE já lançados para este aluno — deixam de ser editáveis
            # aqui; uma correcção passa a ter de ser feita fora deste ecrã.
            form.fields['mac'].widget.attrs['disabled'] = 'disabled'
            form.fields['npt'].widget.attrs['disabled'] = 'disabled'
        linhas.append({
            'aluno': aluno,
            'form': form,
            'mt1': medias_anteriores.get(aluno.id, {}).get('mt1'),
            'mt2': medias_anteriores.get(aluno.id, {}).get('mt2'),
            'resultado_disciplina': resultados_por_aluno.get(aluno.id),
            'nota_gravada': nota_gravada,
        })

    contexto.update({
        'avaliacao': avaliacao,
        'formset': formset,
        'linhas': linhas,
        'pode_editar': pode_editar,
        'periodo_ativo': periodo_ativo,
        'eh_terceiro_trimestre': campo_periodo(periodo) == 'mt3' if periodo else False,
        'eh_terceiro_trimestre_iiano': eh_terceiro_trimestre_iiano,
        'mostrar_mt1': 'mt1' in campos_anteriores,
        'mostrar_mt2': 'mt2' in campos_anteriores,
    })
    return render(request, 'pautas/lancamento_notas.html', contexto)


def _media(valores):
    valores = list(valores)
    if not valores:
        return None
    return round(sum(valores) / len(valores), 1)


@admin_ou_professor_requerido
def relatorios_professor(request):
    atribuicoes = AtribuicaoDocente.objects.filter(ativo=True).select_related(
        'disciplina', 'turma', 'ano_letivo'
    )
    if not eh_subdiretor_pedagogico(request.user):
        atribuicoes = atribuicoes.filter(professor__user=request.user)
    atribuicoes = atribuicoes.order_by('turma__classe__nome', 'turma__nome', 'disciplina__nome')

    turmas = (
        Turma.objects
        .filter(atribuicaodocente__in=atribuicoes)
        .distinct()
        .order_by('classe__nome', 'nome')
    )

    pares = {(a.turma_id, a.disciplina_id, a.ano_letivo_id) for a in atribuicoes}
    turma_ids = {p[0] for p in pares}
    disciplina_ids = {p[1] for p in pares}

    alunos_scoped = Aluno.objects.filter(
        turma_id__in=turma_ids, estado=Aluno.ESTADO_ATIVO
    ).select_related('turma').distinct()

    resultados_todos = ResultadoDisciplina.objects.filter(
        aluno__turma_id__in=turma_ids, disciplina_id__in=disciplina_ids,
    ).select_related('aluno', 'aluno__turma', 'disciplina')
    resultados = [
        r for r in resultados_todos
        if (r.aluno.turma_id, r.disciplina_id, r.ano_letivo_id) in pares
    ]
    resultados_com_notas = [r for r in resultados if r.mf and r.mf > 0]

    total_alunos = alunos_scoped.count()
    total_turmas = turmas.count()
    media_geral = _media(r.mf for r in resultados_com_notas)

    aprovados = sum(1 for r in resultados_com_notas if r.resultado == ResultadoDisciplina.RESULTADO_APROVADO)
    reprovados = sum(
        1 for r in resultados_com_notas
        if r.resultado in (ResultadoDisciplina.RESULTADO_REPROVADO, ResultadoDisciplina.RESULTADO_DEFICIENCIA)
    )
    total_avaliados = len(resultados_com_notas)
    taxa_aprovacao = round(aprovados / total_avaliados * 100, 1) if total_avaliados else 0
    taxa_reprovacao = round(reprovados / total_avaliados * 100, 1) if total_avaliados else 0

    disciplinas_labels = []
    disciplinas_dados = []
    por_disciplina = {}
    for r in resultados_com_notas:
        por_disciplina.setdefault(r.disciplina.nome, []).append(float(r.mf))
    for nome, valores in sorted(por_disciplina.items()):
        disciplinas_labels.append(nome)
        disciplinas_dados.append(_media(valores))

    evolucao_labels = ['1º Trimestre', '2º Trimestre', '3º Trimestre']
    evolucao_dados = [
        _media(float(r.mt1) for r in resultados_com_notas if r.mt1 and r.mt1 > 0) or 0,
        _media(float(r.mt2) for r in resultados_com_notas if r.mt2 and r.mt2 > 0) or 0,
        _media(float(r.mt3) for r in resultados_com_notas if r.mt3 and r.mt3 > 0) or 0,
    ]

    medias_por_aluno = {}
    for r in resultados_com_notas:
        medias_por_aluno.setdefault(r.aluno, []).append(float(r.mf))

    alunos_risco = sorted(
        (
            {'aluno': aluno, 'turma': aluno.turma, 'media': _media(valores)}
            for aluno, valores in medias_por_aluno.items()
            if _media(valores) is not None and _media(valores) < 10
        ),
        key=lambda item: item['media'],
    )[:10]

    melhores_medias = sorted(
        (
            {'aluno': aluno, 'turma': aluno.turma, 'media': _media(valores)}
            for aluno, valores in medias_por_aluno.items()
        ),
        key=lambda item: item['media'],
        reverse=True,
    )[:5]

    contexto = {
        'atribuicoes': atribuicoes,
        'turmas': turmas,
        'total_alunos': total_alunos,
        'total_turmas': total_turmas,
        'media_geral': media_geral,
        'taxa_aprovacao': taxa_aprovacao,
        'taxa_reprovacao': taxa_reprovacao,
        'disciplinas_labels': disciplinas_labels,
        'disciplinas_dados': disciplinas_dados,
        'evolucao_labels': evolucao_labels,
        'evolucao_dados': evolucao_dados,
        'alunos_risco': alunos_risco,
        'melhores_medias': melhores_medias,
    }
    return render(request, 'pautas/relatorios.html', contexto)


class NotaListView(AdminOuProfessorRequeridoMixin, ListView):
    model = Nota
    template_name = 'pautas/lista_notas.html'
    context_object_name = 'notas'

    def get_queryset(self):
        queryset = (
            Nota.objects
            .select_related(
                'aluno',
                'avaliacao__periodo',
                'avaliacao__atribuicao__disciplina',
                'avaliacao__atribuicao__turma',
            )
            .order_by('avaliacao__periodo__nome', 'aluno__nome')
        )

        if not eh_subdiretor_pedagogico(self.request.user):
            queryset = queryset.filter(
                avaliacao__atribuicao__professor__user=self.request.user
            )

        return queryset


@admin_ou_professor_requerido
def pauta_turma(request, turma_id):
    turma = get_object_or_404(Turma, id=turma_id)
    alunos = Aluno.objects.filter(turma=turma, estado=Aluno.ESTADO_ATIVO).order_by('nome')
    context = {'turma': turma, 'alunos': alunos}
    return render(request, 'pautas/pauta_turma.html', context)


@admin_ou_professor_requerido
def pauta_trimestral(request, avaliacao_id):
    avaliacao = get_object_or_404(
        Avaliacao.objects.select_related(
            'periodo',
            'atribuicao__professor__user',
            'atribuicao__disciplina',
            'atribuicao__turma',
            'atribuicao__ano_letivo',
        ),
        pk=avaliacao_id,
    )

    if not _pode_ver_avaliacao(request.user, avaliacao):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    notas = notas_da_avaliacao(avaliacao)

    return render(
        request,
        'pautas/pauta_trimestral.html',
        {
            'avaliacao': avaliacao,
            'notas': notas,
            'form_importacao': ImportarNotasExcelForm(),
            'form_erro_validacao': ObservacoesValidacaoForm(),
            'eh_subdiretor_pedagogico': eh_subdiretor_pedagogico(request.user),
            'pode_editar': _eh_professor_titular(request.user, avaliacao),
        },
    )


@admin_ou_professor_requerido
def baixar_modelo_excel(request, avaliacao_id):
    avaliacao = get_object_or_404(Avaliacao, pk=avaliacao_id)

    if not _pode_ver_avaliacao(request.user, avaliacao):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    arquivo = criar_modelo_excel(avaliacao)
    nome = f'modelo_pauta_{avaliacao.id}.xlsx'
    return FileResponse(
        arquivo,
        as_attachment=True,
        filename=nome,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@admin_ou_professor_requerido
def exportar_excel(request, avaliacao_id):
    avaliacao = get_object_or_404(Avaliacao, pk=avaliacao_id)

    if not _pode_ver_avaliacao(request.user, avaliacao):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    arquivo = exportar_pauta_excel(avaliacao, notas_da_avaliacao(avaliacao))
    nome = f'pauta_{avaliacao.id}.xlsx'
    return FileResponse(
        arquivo,
        as_attachment=True,
        filename=nome,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@professor_requerido
def importar_excel(request, avaliacao_id):
    avaliacao = get_object_or_404(
        Avaliacao.objects.select_related('periodo', 'atribuicao__professor__user'),
        pk=avaliacao_id,
    )

    if avaliacao.atribuicao.professor.user_id != request.user.id:
        return render(request, 'dashboards/sem_permissao.html', status=403)

    if request.method != 'POST':
        return redirect('pauta_trimestral', avaliacao_id=avaliacao.id)

    if not avaliacao.periodo.periodo_lancamento_ativo():
        messages.error(request, 'Fora do período de lançamento de notas para este trimestre.')
        return redirect('pauta_trimestral', avaliacao_id=avaliacao.id)

    form = ImportarNotasExcelForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, 'Selecione um arquivo Excel valido.')
        return redirect('pauta_trimestral', avaliacao_id=avaliacao.id)

    resultado = importar_notas_excel(
        avaliacao,
        form.cleaned_data['arquivo'],
    )

    if resultado['erros']:
        for erro in resultado['erros'][:5]:
            messages.warning(request, erro)
        if len(resultado['erros']) > 5:
            messages.warning(
                request,
                f"Existem mais {len(resultado['erros']) - 5} erros no arquivo.",
            )

    messages.success(
        request,
        (
            f"Importacao concluida: {resultado['criados']} notas criadas e "
            f"{resultado['atualizados']} atualizadas."
        ),
    )
    return redirect('pauta_trimestral', avaliacao_id=avaliacao.id)


@admin_ou_professor_requerido
def exportar_pdf(request, avaliacao_id):
    avaliacao = get_object_or_404(Avaliacao, pk=avaliacao_id)

    if not _pode_ver_avaliacao(request.user, avaliacao):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    arquivo = exportar_pauta_pdf(avaliacao, notas_da_avaliacao(avaliacao))
    nome = f'pauta_{avaliacao.id}.pdf'
    return FileResponse(
        arquivo,
        as_attachment=True,
        filename=nome,
        content_type='application/pdf',
    )


@subdiretor_pedagogico_requerido
def gerar_resultados(request):
    total = gerar_resultados_finais()
    messages.success(request, f'{total} resultados finais gerados com sucesso.')
    return redirect('resultado_lista')


@subdiretor_pedagogico_requerido
def avaliacao_validar(request, avaliacao_id):
    avaliacao = get_object_or_404(Avaliacao, pk=avaliacao_id)
    avaliacao.marcar_validada(request.user)
    messages.success(request, 'Avaliação validada e disponibilizada.')
    # Volta directamente à lista de Avaliações (não à pauta trimestral) —
    # é daí que o admin costuma validar várias pautas seguidas, e assim
    # poupa o clique extra de ter de voltar atrás manualmente.
    return redirect('avaliacao_lista')


@subdiretor_pedagogico_requerido
def avaliacao_reportar_erro(request, avaliacao_id):
    avaliacao = get_object_or_404(
        Avaliacao.objects.select_related(
            'atribuicao__professor__user',
            'atribuicao__turma',
            'atribuicao__disciplina',
            'atribuicao__ano_letivo',
        ),
        pk=avaliacao_id,
    )

    if request.method != 'POST':
        return redirect('pauta_trimestral', avaliacao_id=avaliacao.id)

    form = ObservacoesValidacaoForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Indique as observações do erro encontrado.')
        return redirect('pauta_trimestral', avaliacao_id=avaliacao.id)

    observacoes = form.cleaned_data['observacoes_validacao']
    avaliacao.marcar_com_erros(request.user, observacoes)

    diretor = DiretorTurma.objects.filter(
        turma=avaliacao.atribuicao.turma,
        ano_letivo=avaliacao.atribuicao.ano_letivo,
        ativo=True,
    ).select_related('professor__user').first()

    if not diretor:
        messages.warning(request, 'Não há diretor de turma definido; apenas o professor foi notificado.')

    notificar_erro_pauta(
        professor_user=avaliacao.atribuicao.professor.user,
        diretor_user=diretor.professor.user if diretor else None,
        titulo=f'Erros na pauta de {avaliacao.atribuicao.disciplina} - {avaliacao.atribuicao.turma}',
        mensagem=observacoes,
        link_url=reverse('pauta_trimestral', kwargs={'avaliacao_id': avaliacao.id}),
    )

    messages.success(request, 'Erro reportado e professor/diretor notificados.')
    return redirect('avaliacao_lista')


def _turma_e_ano_da_pauta_final(request):
    turma_id = request.GET.get('turma')
    ano_letivo_id = request.GET.get('ano_letivo')

    turma = get_object_or_404(Turma, pk=turma_id) if turma_id else None
    ano_letivo = (
        get_object_or_404(AnoLetivo, pk=ano_letivo_id)
        if ano_letivo_id
        else AnoLetivo.objects.filter(ativo=True).first()
    )
    return turma, ano_letivo


@admin_ou_professor_requerido
def pauta_final_turma(request):
    turma, ano_letivo = _turma_e_ano_da_pauta_final(request)

    turmas = list(Turma.objects.filter(ativo=True).order_by('classe__nome', 'nome'))

    # Turma anterior/seguinte na mesma ordenação — usadas pela navegação por
    # teclado (setas esquerda/direita) no template.
    turma_anterior = turma_seguinte = None
    if turma:
        indices = [i for i, t in enumerate(turmas) if t.id == turma.id]
        if indices:
            indice = indices[0]
            if indice > 0:
                turma_anterior = turmas[indice - 1]
            if indice < len(turmas) - 1:
                turma_seguinte = turmas[indice + 1]

    contexto = {
        'turma': turma,
        'ano_letivo': ano_letivo,
        'turmas': turmas,
        'turma_anterior': turma_anterior,
        'turma_seguinte': turma_seguinte,
        'anos_letivos': AnoLetivo.objects.all(),
        'disciplinas': [],
        'linhas': [],
    }

    if not turma:
        return render(request, 'pautas/pauta_final_turma.html', contexto)

    if not _pode_ver_pauta_final(request.user, turma, ano_letivo):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    if ano_letivo:
        disciplinas, linhas = montar_pauta_final_turma(turma, ano_letivo)
        contexto['disciplinas'] = disciplinas
        contexto['linhas'] = linhas

    return render(request, 'pautas/pauta_final_turma.html', contexto)


@admin_ou_professor_requerido
def aluno_resumo_resultados(request, aluno_id):
    """Fragmento HTML (sem base.html) com os resultados finais de um aluno,
    usado como conteúdo do modal de visualização rápida na pauta final —
    ver pautas/pauta_final_turma.html e static/js/pauta_final_zoom.js."""
    aluno = get_object_or_404(Aluno, pk=aluno_id)
    ano_letivo_id = request.GET.get('ano_letivo')
    ano_letivo = (
        get_object_or_404(AnoLetivo, pk=ano_letivo_id)
        if ano_letivo_id
        else AnoLetivo.objects.filter(ativo=True).first()
    )

    if not _pode_ver_pauta_final(request.user, aluno.turma, ano_letivo):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    resultados = []
    situacao_anual = None
    if ano_letivo:
        resultados = list(
            ResultadoDisciplina.objects
            .filter(aluno=aluno, ano_letivo=ano_letivo)
            .select_related('disciplina')
            .order_by('disciplina__nome')
        )
        situacao_anual = SituacaoAnual.objects.filter(aluno=aluno, ano_letivo=ano_letivo).first()

    return render(request, 'pautas/_aluno_resumo_resultados.html', {
        'aluno': aluno,
        'ano_letivo': ano_letivo,
        'resultados': resultados,
        'situacao_anual': situacao_anual,
    })


FAIXAS_NOTA = [
    ('0 - 4,9', 0, 5),
    ('5,0 - 9,9', 5, 10),
    ('10,0 - 13,9', 10, 14),
    ('14,0 - 16,9', 14, 17),
    ('17,0 - 20', 17, 21),
]


def _distribuicao_notas(valores):
    total = len(valores)
    distribuicao = []
    for rotulo, minimo, maximo in FAIXAS_NOTA:
        n = sum(1 for v in valores if minimo <= v < maximo)
        distribuicao.append({
            'faixa': rotulo,
            'n': n,
            'pct': round(n / total * 100, 1) if total else 0,
        })
    return distribuicao


def _stats_trimestre(valores):
    if not valores:
        return None
    aprovados = sum(1 for v in valores if v >= 10)
    return {
        'n': len(valores),
        'media': round(sum(valores) / len(valores), 1),
        'maior': max(valores),
        'menor': min(valores),
        'taxa_aprovacao': round(aprovados / len(valores) * 100, 1),
        'distribuicao': _distribuicao_notas(valores),
    }


@admin_ou_professor_requerido
def boletim_disciplina_turma(request, disciplina_id, turma_id):
    """Boletim estatístico de uma disciplina numa turma ao longo do ano
    lectivo (3 trimestres + resumo final) — acedido a partir do nome da
    disciplina na pauta final (pautas/pauta_final_turma.html)."""
    turma = get_object_or_404(Turma, pk=turma_id)
    disciplina = get_object_or_404(Disciplina, pk=disciplina_id)
    ano_letivo_id = request.GET.get('ano_letivo')
    ano_letivo = (
        get_object_or_404(AnoLetivo, pk=ano_letivo_id)
        if ano_letivo_id
        else AnoLetivo.objects.filter(ativo=True).first()
    )

    if not _pode_ver_pauta_final(request.user, turma, ano_letivo):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    atribuicao = AtribuicaoDocente.objects.filter(
        disciplina=disciplina, turma=turma, ano_letivo=ano_letivo
    ).select_related('professor__user').first()

    resultados = []
    if ano_letivo:
        resultados = list(
            ResultadoDisciplina.objects
            .filter(disciplina=disciplina, aluno__turma=turma, ano_letivo=ano_letivo)
        )

    trimestres = []
    for numero, campo in enumerate(('mt1', 'mt2', 'mt3'), start=1):
        valores = [float(getattr(r, campo)) for r in resultados if getattr(r, campo) is not None]
        trimestres.append({'numero': numero, 'stats': _stats_trimestre(valores)})

    resumo = None
    desvio_padrao = None
    coeficiente_rendimento = None
    evolucao_media = None

    if resultados:
        medias_finais = [float(r.mf) for r in resultados]
        aprovados = sum(1 for r in resultados if r.resultado == ResultadoDisciplina.RESULTADO_APROVADO)
        reprovados = len(resultados) - aprovados
        media_geral = sum(medias_finais) / len(medias_finais)

        resumo = {
            'n': len(resultados),
            'media_geral': round(media_geral, 1),
            'maior_media': max(medias_finais),
            'menor_media': min(medias_finais),
            'taxa_aprovacao': round(aprovados / len(resultados) * 100, 1),
            'aprovados': aprovados,
            'reprovados': reprovados,
            'distribuicao': _distribuicao_notas(medias_finais),
        }
        desvio_padrao = round(statistics.stdev(medias_finais), 1) if len(medias_finais) > 1 else 0
        coeficiente_rendimento = round(media_geral / 20 * 100, 1)

        stats_t1, stats_t3 = trimestres[0]['stats'], trimestres[2]['stats']
        if stats_t1 and stats_t3:
            evolucao_media = round(stats_t3['media'] - stats_t1['media'], 1)

    from core.models import Escola

    contexto = {
        'turma': turma,
        'disciplina': disciplina,
        'ano_letivo': ano_letivo,
        'escola': Escola.obter_configuracao(),
        'professor': atribuicao.professor if atribuicao else None,
        'trimestres': trimestres,
        'resumo': resumo,
        'desvio_padrao': desvio_padrao,
        'coeficiente_rendimento': coeficiente_rendimento,
        'evolucao_media': evolucao_media,
        'evolucao_labels': ['1º Trimestre', '2º Trimestre', '3º Trimestre'],
        'evolucao_medias': [t['stats']['media'] if t['stats'] else 0 for t in trimestres],
        'evolucao_taxas': [t['stats']['taxa_aprovacao'] if t['stats'] else 0 for t in trimestres],
        'faixas_labels': [f[0] for f in FAIXAS_NOTA],
        'distrib_t1': [f['n'] for f in trimestres[0]['stats']['distribuicao']] if trimestres[0]['stats'] else [],
        'distrib_t2': [f['n'] for f in trimestres[1]['stats']['distribuicao']] if trimestres[1]['stats'] else [],
        'distrib_t3': [f['n'] for f in trimestres[2]['stats']['distribuicao']] if trimestres[2]['stats'] else [],
        'distrib_final': [f['n'] for f in resumo['distribuicao']] if resumo else [],
    }
    return render(request, 'pautas/boletim_disciplina.html', contexto)


@admin_ou_professor_requerido
def pauta_final_exportar_pdf(request):
    turma, ano_letivo = _turma_e_ano_da_pauta_final(request)

    if not turma or not ano_letivo:
        return render(request, 'dashboards/sem_permissao.html', status=403)
    if not _pode_ver_pauta_final(request.user, turma, ano_letivo):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    disciplinas, linhas = montar_pauta_final_turma(turma, ano_letivo)
    arquivo = exportar_pauta_final_pdf(turma, ano_letivo, disciplinas, linhas)
    nome = f'pauta_final_{turma.id}_{ano_letivo.id}.pdf'
    return FileResponse(
        arquivo,
        as_attachment=True,
        filename=nome,
        content_type='application/pdf',
    )


def _turma_disciplina_e_ano_da_mini_pauta(request):
    turma_id = request.GET.get('turma')
    disciplina_id = request.GET.get('disciplina')
    ano_letivo_id = request.GET.get('ano_letivo')

    turma = get_object_or_404(Turma, pk=turma_id) if turma_id else None
    disciplina = get_object_or_404(Disciplina, pk=disciplina_id) if disciplina_id else None
    ano_letivo = (
        get_object_or_404(AnoLetivo, pk=ano_letivo_id)
        if ano_letivo_id
        else AnoLetivo.objects.filter(ativo=True).first()
    )
    return turma, disciplina, ano_letivo


def _pode_ver_mini_pauta(user, turma, disciplina, ano_letivo):
    if eh_subdiretor_pedagogico(user):
        return True
    if AtribuicaoDocente.objects.filter(
        professor__user=user, turma=turma, disciplina=disciplina, ano_letivo=ano_letivo
    ).exists():
        return True
    return _eh_diretor_da_turma(user, turma, ano_letivo)


def _pode_editar_mini_pauta(user, turma, disciplina, ano_letivo):
    # Só quem lança notas (professor titular) ou o admin — ao contrário de
    # _pode_ver_mini_pauta, o diretor de turma não entra aqui: só pode
    # consultar, não lançar NER de uma disciplina que não é sua.
    if eh_subdiretor_pedagogico(user):
        return True
    return AtribuicaoDocente.objects.filter(
        professor__user=user, turma=turma, disciplina=disciplina, ano_letivo=ano_letivo, ativo=True
    ).exists()


@admin_ou_professor_requerido
def mini_pauta_trimestral(request):
    turma, disciplina, ano_letivo = _turma_disciplina_e_ano_da_mini_pauta(request)

    contexto = {
        'turma': turma,
        'disciplina': disciplina,
        'ano_letivo': ano_letivo,
        'turmas': Turma.objects.filter(ativo=True).order_by('classe__nome', 'nome'),
        'disciplinas': Disciplina.objects.filter(ativa=True).order_by('nome'),
        'anos_letivos': AnoLetivo.objects.all(),
        'linhas': [],
        'pode_editar_ner': False,
    }

    if not (turma and disciplina and ano_letivo):
        return render(request, 'pautas/mini_pauta_trimestral.html', contexto)

    if not _pode_ver_mini_pauta(request.user, turma, disciplina, ano_letivo):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    pode_editar_ner = turma.eh_segundo_ano() and _pode_editar_mini_pauta(
        request.user, turma, disciplina, ano_letivo
    )

    if request.method == 'POST':
        if not pode_editar_ner:
            return render(request, 'dashboards/sem_permissao.html', status=403)
        alunos = list(Aluno.objects.filter(turma=turma, estado=Aluno.ESTADO_ATIVO))
        ner_gravadas, erros = _gravar_notas_recurso(request, alunos, disciplina, ano_letivo)
        if ner_gravadas:
            messages.success(request, f'{ner_gravadas} nota(s) de recurso (NER) gravada(s).')
        if erros:
            messages.warning(request, 'Não foi possível gravar: ' + '; '.join(erros))
        return redirect(
            f"{reverse('mini_pauta_trimestral')}"
            f"?turma={turma.id}&disciplina={disciplina.id}&ano_letivo={ano_letivo.id}"
        )

    contexto['linhas'] = montar_mini_pauta_disciplina(disciplina, turma, ano_letivo)
    contexto['pode_editar_ner'] = pode_editar_ner
    return render(request, 'pautas/mini_pauta_trimestral.html', contexto)


@admin_ou_professor_requerido
def mini_pauta_exportar_excel(request):
    turma, disciplina, ano_letivo = _turma_disciplina_e_ano_da_mini_pauta(request)

    if not (turma and disciplina and ano_letivo):
        return render(request, 'dashboards/sem_permissao.html', status=403)
    if not _pode_ver_mini_pauta(request.user, turma, disciplina, ano_letivo):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    linhas = montar_mini_pauta_disciplina(disciplina, turma, ano_letivo)
    arquivo = exportar_mini_pauta_excel(turma, disciplina, ano_letivo, linhas)
    nome = f'mini_pauta_{disciplina.id}_{turma.id}_{ano_letivo.id}.xlsx'
    return FileResponse(
        arquivo,
        as_attachment=True,
        filename=nome,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@admin_ou_professor_requerido
def mini_pauta_exportar_pdf(request):
    turma, disciplina, ano_letivo = _turma_disciplina_e_ano_da_mini_pauta(request)

    if not (turma and disciplina and ano_letivo):
        return render(request, 'dashboards/sem_permissao.html', status=403)
    if not _pode_ver_mini_pauta(request.user, turma, disciplina, ano_letivo):
        return render(request, 'dashboards/sem_permissao.html', status=403)

    linhas = montar_mini_pauta_disciplina(disciplina, turma, ano_letivo)
    arquivo = exportar_mini_pauta_pdf(turma, disciplina, ano_letivo, linhas)
    nome = f'mini_pauta_{disciplina.id}_{turma.id}_{ano_letivo.id}.pdf'
    return FileResponse(
        arquivo,
        as_attachment=True,
        filename=nome,
        content_type='application/pdf',
    )


@subdiretor_pedagogico_requerido
def resultado_validar(request, pk):
    resultado = get_object_or_404(ResultadoDisciplina, pk=pk)
    resultado.marcar_validada(request.user)
    messages.success(request, 'Resultado final validado e disponibilizado.')
    return redirect('resultado_lista')


@subdiretor_pedagogico_requerido
def resultado_reportar_erro(request, pk):
    resultado = get_object_or_404(
        ResultadoDisciplina.objects.select_related('aluno__turma', 'disciplina', 'ano_letivo'),
        pk=pk,
    )

    if request.method != 'POST':
        return redirect('resultado_lista')

    form = ObservacoesValidacaoForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Indique as observações do erro encontrado.')
        return redirect('resultado_lista')

    observacoes = form.cleaned_data['observacoes_validacao']
    resultado.marcar_com_erros(request.user, observacoes)

    atribuicao = AtribuicaoDocente.objects.filter(
        disciplina=resultado.disciplina,
        turma=resultado.aluno.turma,
        ano_letivo=resultado.ano_letivo,
        ativo=True,
    ).select_related('professor__user').first()

    diretor = DiretorTurma.objects.filter(
        turma=resultado.aluno.turma,
        ano_letivo=resultado.ano_letivo,
        ativo=True,
    ).select_related('professor__user').first()

    if not atribuicao:
        messages.warning(request, 'Não foi encontrada a atribuição docente correspondente; verifique manualmente.')
    if not diretor:
        messages.warning(request, 'Não há diretor de turma definido para esta turma/ano.')

    notificar_erro_pauta(
        professor_user=atribuicao.professor.user if atribuicao else None,
        diretor_user=diretor.professor.user if diretor else None,
        titulo=f'Erros no resultado final de {resultado.disciplina} - {resultado.aluno.turma}',
        mensagem=observacoes,
        link_url=reverse('resultado_lista'),
    )

    messages.success(request, 'Erro reportado e notificações enviadas.')
    return redirect('resultado_lista')


class NotaCreateView(ProfessorRequeridoMixin, CreateView):
    model = Nota
    form_class = NotaForm
    template_name = 'pautas/forms.html'
    success_url = reverse_lazy('nota_lista')


class NotaUpdateView(ProfessorRequeridoMixin, UpdateView):
    model = Nota
    form_class = NotaForm
    template_name = 'pautas/forms.html'
    success_url = reverse_lazy('nota_lista')

    def get_queryset(self):
        return Nota.objects.filter(avaliacao__atribuicao__professor__user=self.request.user)


class NotaDeleteView(ProfessorRequeridoMixin, DeleteView):
    model = Nota
    template_name = 'pautas/excluir.html'
    success_url = reverse_lazy('nota_lista')

    def get_queryset(self):
        return Nota.objects.filter(avaliacao__atribuicao__professor__user=self.request.user)


class AvaliacaoListView(AdminOuProfessorRequeridoMixin, ListView):
    model = Avaliacao
    template_name = 'pautas/avaliacao_lista.html'
    context_object_name = 'avaliacoes'

    def get_queryset(self):
        queryset = (
            Avaliacao.objects
            .select_related(
                'periodo',
                'atribuicao__professor__user',
                'atribuicao__disciplina',
                'atribuicao__turma',
            )
            .order_by('-criado_em')
        )

        if not eh_subdiretor_pedagogico(self.request.user):
            queryset = queryset.filter(atribuicao__professor__user=self.request.user)

        turma_id = self.request.GET.get('turma')
        disciplina_id = self.request.GET.get('disciplina')
        periodo_id = self.request.GET.get('periodo')
        status = self.request.GET.get('status')

        if turma_id:
            queryset = queryset.filter(atribuicao__turma_id=turma_id)
        if disciplina_id:
            queryset = queryset.filter(atribuicao__disciplina_id=disciplina_id)
        if periodo_id:
            queryset = queryset.filter(periodo_id=periodo_id)
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['turmas'] = Turma.objects.filter(ativo=True).order_by('classe__nome', 'nome')
        context['disciplinas'] = Disciplina.objects.all().order_by('nome')
        context['periodos'] = PeriodoAcademico.objects.select_related('ano_letivo').order_by(
            '-ano_letivo__descricao', 'nome'
        )
        context['status_choices'] = Avaliacao.STATUS_CHOICES
        context['eh_subdiretor_pedagogico'] = eh_subdiretor_pedagogico(self.request.user)
        return context


class AvaliacaoCreateView(ProfessorRequeridoMixin, CreateView):
    model = Avaliacao
    form_class = AvaliacaoForm
    template_name = 'pautas/avaliacao_form.html'
    success_url = reverse_lazy('avaliacao_lista')


class AvaliacaoUpdateView(ProfessorRequeridoMixin, UpdateView):
    model = Avaliacao
    form_class = AvaliacaoForm
    template_name = 'pautas/avaliacao_form.html'
    success_url = reverse_lazy('avaliacao_lista')

    def get_queryset(self):
        return Avaliacao.objects.filter(atribuicao__professor__user=self.request.user)


class AvaliacaoDeleteView(ProfessorRequeridoMixin, DeleteView):
    model = Avaliacao
    template_name = 'pautas/avaliacao_excluir.html'
    success_url = reverse_lazy('avaliacao_lista')

    def get_queryset(self):
        return Avaliacao.objects.filter(atribuicao__professor__user=self.request.user)


class ResultadoDisciplinaListView(AdminOuProfessorRequeridoMixin, ListView):
    model = ResultadoDisciplina
    template_name = 'pautas/resultado_lista.html'
    context_object_name = 'resultados'

    def get_queryset(self):
        queryset = (
            ResultadoDisciplina.objects
            .select_related('aluno', 'aluno__turma', 'disciplina', 'ano_letivo')
            .order_by('aluno__nome', 'disciplina__nome')
        )

        if not eh_subdiretor_pedagogico(self.request.user):
            disciplinas_professor = AtribuicaoDocente.objects.filter(
                professor__user=self.request.user
            ).values('disciplina')
            queryset = queryset.filter(disciplina__in=disciplinas_professor)

        turma_id = self.request.GET.get('turma')
        disciplina_id = self.request.GET.get('disciplina')
        ano_letivo_id = self.request.GET.get('ano_letivo')
        status = self.request.GET.get('status')
        aluno_id = self.request.GET.get('aluno')

        if turma_id:
            queryset = queryset.filter(aluno__turma_id=turma_id)
        if disciplina_id:
            queryset = queryset.filter(disciplina_id=disciplina_id)
        if ano_letivo_id:
            queryset = queryset.filter(ano_letivo_id=ano_letivo_id)
        if status:
            queryset = queryset.filter(status=status)
        if aluno_id:
            queryset = queryset.filter(aluno_id=aluno_id)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['turmas'] = Turma.objects.filter(ativo=True).order_by('classe__nome', 'nome')
        context['disciplinas'] = Disciplina.objects.all().order_by('nome')
        context['anos_letivos'] = AnoLetivo.objects.all()
        context['status_choices'] = ResultadoDisciplina.STATUS_CHOICES
        context['eh_subdiretor_pedagogico'] = eh_subdiretor_pedagogico(self.request.user)

        aluno_id = self.request.GET.get('aluno')
        if aluno_id:
            context['aluno_filtro'] = Aluno.objects.filter(pk=aluno_id).first()

        return context


class ResultadoDisciplinaCreateView(SuperuserRequeridoMixin, CreateView):
    model = ResultadoDisciplina
    form_class = ResultadoDisciplinaForm
    template_name = 'pautas/resultado_form.html'
    success_url = reverse_lazy('resultado_lista')


class ResultadoDisciplinaUpdateView(SuperuserRequeridoMixin, UpdateView):
    model = ResultadoDisciplina
    form_class = ResultadoDisciplinaForm
    template_name = 'pautas/resultado_form.html'
    success_url = reverse_lazy('resultado_lista')


class ResultadoDisciplinaDeleteView(SuperuserRequeridoMixin, DeleteView):
    model = ResultadoDisciplina
    template_name = 'pautas/resultado_excluir.html'
    success_url = reverse_lazy('resultado_lista')


def _pautas_validadas_do_aluno(aluno):
    resultados_por_disciplina = {
        resultado.disciplina_id: resultado
        for resultado in ResultadoDisciplina.objects.filter(
            aluno=aluno, status=ResultadoDisciplina.STATUS_VALIDADA
        ).select_related('disciplina', 'ano_letivo')
    }

    notas = (
        Nota.objects
        .filter(aluno=aluno, avaliacao__status=Avaliacao.STATUS_VALIDADA)
        .select_related(
            'avaliacao__periodo',
            'avaliacao__atribuicao__disciplina',
        )
        .order_by('avaliacao__atribuicao__disciplina__nome', 'avaliacao__periodo__nome')
    )

    disciplinas = {}
    for nota in notas:
        disciplina = nota.avaliacao.atribuicao.disciplina
        info = disciplinas.setdefault(disciplina.id, {
            'disciplina': disciplina,
            'notas': [],
            'resultado': resultados_por_disciplina.get(disciplina.id),
        })
        info['notas'].append(nota)

    for disciplina_id, resultado in resultados_por_disciplina.items():
        if disciplina_id not in disciplinas:
            disciplinas[disciplina_id] = {
                'disciplina': resultado.disciplina,
                'notas': [],
                'resultado': resultado,
            }

    return {
        'disciplinas': sorted(disciplinas.values(), key=lambda info: info['disciplina'].nome),
    }


@aluno_requerido
def minhas_notas(request):
    aluno = getattr(request.user, 'aluno', None)

    if aluno is None:
        return render(request, 'pautas/minhas_notas.html', {'aluno': None})

    contexto = _pautas_validadas_do_aluno(aluno)
    contexto['aluno'] = aluno
    return render(request, 'pautas/minhas_notas.html', contexto)


@encarregado_requerido
def meus_dependentes(request):
    dependentes = Aluno.objects.filter(
        encarregado=request.user.encarregado
    ).order_by('nome')
    return render(request, 'pautas/meus_dependentes.html', {'dependentes': dependentes})


@encarregado_requerido
def notas_dependente(request, aluno_id):
    aluno = get_object_or_404(Aluno.objects.select_related('encarregado__user'), pk=aluno_id)

    if aluno.encarregado.user_id != request.user.id:
        return render(request, 'dashboards/sem_permissao.html', status=403)

    contexto = _pautas_validadas_do_aluno(aluno)
    contexto['aluno'] = aluno
    return render(request, 'pautas/minhas_notas.html', contexto)
