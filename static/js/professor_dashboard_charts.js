document.addEventListener('DOMContentLoaded', function () {
    const dados = window.PROF_DASHBOARD_DADOS || {};

    function gaugeCorTexto(valor) {
        if (valor === null || valor === undefined) return '#adb5bd';
        if (valor < 50) return '#dc3545';
        if (valor < 75) return '#fd7e14';
        return '#198754';
    }

    // Mesma técnica de "gauge" (doughnut + texto central desenhado à mão via
    // plugin afterDraw) usada em static/js/aluno_charts.js:criarAnel — ver
    // comentário lá para a explicação da técnica.
    function desenharGauge(id, valor, max, sufixo) {
        const el = document.getElementById(id);
        if (!el) return;

        const restante = Math.max((max || 100) - (valor || 0), 0);
        const cor = gaugeCorTexto(max === 20 ? (valor / 20) * 100 : valor);

        new Chart(el, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: valor === null || valor === undefined ? [1] : [valor, restante],
                    backgroundColor: valor === null || valor === undefined
                        ? ['#e9ecef']
                        : [cor, '#e9ecef'],
                    borderWidth: 0,
                }],
            },
            options: {
                responsive: true,
                cutout: '75%',
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false },
                },
            },
            plugins: [{
                id: 'texto-central-' + id,
                afterDraw(chart) {
                    const { ctx, chartArea } = chart;
                    const texto = valor === null || valor === undefined ? '—' : `${valor}${sufixo}`;
                    const x = (chartArea.left + chartArea.right) / 2;
                    const y = (chartArea.top + chartArea.bottom) / 2;
                    ctx.save();
                    ctx.font = 'bold 1.3rem sans-serif';
                    ctx.fillStyle = '#212529';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(texto, x, y);
                    ctx.restore();
                },
            }],
        });
    }

    // Gauges: frequência média da turma (%) e desempenho médio (0-20)
    desenharGauge('grafico-frequencia-gauge', dados.frequenciaMedia, 100, '%');
    desenharGauge('grafico-desempenho-gauge', dados.desempenhoMedia, 20, '');

    // Mini-gráficos de linha sem eixos (sparklines), um por aluno/disciplina,
    // usados nas tabelas do dashboard do professor para mostrar a tendência
    // de notas num relance. Os valores vêm em data-valores (CSV) no HTML.
    document.querySelectorAll('.prof-dash-sparkline').forEach(function (canvas) {
        const bruto = canvas.dataset.valores || '';
        const valores = bruto.split(',').filter(Boolean).map(Number);
        if (!valores.length) return;

        new Chart(canvas, {
            type: 'line',
            data: {
                labels: valores.map((_, i) => i + 1),
                datasets: [{
                    data: valores,
                    borderColor: '#0d6efd',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.3,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { display: false },
                    y: { display: false },
                },
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false },
                },
            },
        });
    });
});
