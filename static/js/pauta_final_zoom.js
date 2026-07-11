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
});
