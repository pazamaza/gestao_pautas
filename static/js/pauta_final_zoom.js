document.addEventListener('DOMContentLoaded', function () {
    const wrap = document.getElementById('pauta-zoom-wrap');
    const zoomIn = document.getElementById('pauta-zoom-in');
    const zoomOut = document.getElementById('pauta-zoom-out');
    const zoomReset = document.getElementById('pauta-zoom-reset');
    if (!wrap) return;

    const MIN = 0.6;
    const MAX = 1.3;
    const STEP = 0.1;
    const DEFAULT = 0.85;
    let tamanho = DEFAULT;

    function aplicar() {
        wrap.style.fontSize = tamanho + 'rem';
    }

    if (zoomIn) {
        zoomIn.addEventListener('click', function () {
            tamanho = Math.min(MAX, +(tamanho + STEP).toFixed(2));
            aplicar();
        });
    }
    if (zoomOut) {
        zoomOut.addEventListener('click', function () {
            tamanho = Math.max(MIN, +(tamanho - STEP).toFixed(2));
            aplicar();
        });
    }
    if (zoomReset) {
        zoomReset.addEventListener('click', function () {
            tamanho = DEFAULT;
            aplicar();
        });
    }

    aplicar();

    // Navegação por teclado (setas esquerda/direita) entre a turma anterior
    // e a seguinte, na mesma ordenação da pauta final (turmas.py:
    // classe__nome, nome). Ignorado quando o foco está num campo de
    // formulário, para não interferir com a digitação (ex.: pesquisa).
    const linkAnterior = document.getElementById('pauta-nav-anterior');
    const linkSeguinte = document.getElementById('pauta-nav-seguinte');

    document.addEventListener('keydown', function (evento) {
        const alvo = evento.target;
        const emCampoEditavel = alvo && (
            alvo.tagName === 'INPUT' || alvo.tagName === 'SELECT' ||
            alvo.tagName === 'TEXTAREA' || alvo.isContentEditable
        );
        if (emCampoEditavel) return;

        if (evento.key === 'ArrowLeft' && linkAnterior) {
            window.location.href = linkAnterior.getAttribute('href');
        } else if (evento.key === 'ArrowRight' && linkSeguinte) {
            window.location.href = linkSeguinte.getAttribute('href');
        }
    });

    // Clicar no nome do aluno abre uma janela flutuante (modal) só de
    // visualização, com os resultados finais desse aluno — em vez de
    // navegar para outra página. O conteúdo é carregado por fetch a partir
    // de aluno_resumo_resultados (pautas/views.py), um fragmento HTML sem
    // navbar, pensado só para ir dentro do modal.
    const modalElemento = document.getElementById('modalResumoAluno');
    const modalCorpo = document.getElementById('modalResumoAlunoBody');
    if (modalElemento && modalCorpo && window.bootstrap) {
        const modal = new window.bootstrap.Modal(modalElemento);

        document.querySelectorAll('.aluno-nome-link').forEach(function (link) {
            link.addEventListener('click', function (evento) {
                evento.preventDefault();
                const url = link.getAttribute('data-resumo-url');
                modalCorpo.innerHTML = '<div class="text-center text-muted py-4">A carregar…</div>';
                modal.show();

                fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                    .then(function (resposta) {
                        if (!resposta.ok) throw new Error('Falha ao carregar (' + resposta.status + ')');
                        return resposta.text();
                    })
                    .then(function (html) {
                        modalCorpo.innerHTML = html;
                    })
                    .catch(function () {
                        modalCorpo.innerHTML = (
                            '<div class="alert alert-danger mb-0">' +
                            'Não foi possível carregar os resultados. Tenta novamente.</div>'
                        );
                    });
            });
        });
    }
});
