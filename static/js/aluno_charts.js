document.addEventListener('DOMContentLoaded', function () {
    function lerValor(id) {
        const el = document.getElementById(id);
        return el ? parseFloat(JSON.parse(el.textContent)) : 0;
    }

    function lerLista(id) {
        const el = document.getElementById(id);
        return el ? JSON.parse(el.textContent) : [];
    }

    // Desenha um "anel"/gauge (doughnut com um buraco grande, cutout: 75%,
    // e um texto escrito no centro via um plugin custom 'afterDraw' — o
    // Chart.js não tem texto central nativo em doughnuts, por isso o valor
    // é desenhado manualmente no canvas depois do gráfico ser renderizado).
    // Mesma técnica duplicada em static/js/professor_dashboard_charts.js.
    function criarAnel(canvasId, valor, max, cor, texto) {
        const el = document.getElementById(canvasId);
        if (!el) {
            return;
        }
        const restante = Math.max(max - valor, 0);

        new Chart(el, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [valor, restante],
                    backgroundColor: [cor, '#e9ecef'],
                    borderWidth: 0,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '75%',
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
            },
            plugins: [{
                id: 'textoCentro',
                afterDraw(chart) {
                    const { ctx, chartArea } = chart;
                    const x = (chartArea.left + chartArea.right) / 2;
                    const y = (chartArea.top + chartArea.bottom) / 2;
                    ctx.save();
                    ctx.font = 'bold 1.1rem sans-serif';
                    ctx.fillStyle = cor;
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(texto, x, y);
                    ctx.restore();
                },
            }],
        });
    }

    const media = lerValor('media-geral-valor');
    criarAnel('anel-media', media, 20, '#198754', `${media}/20`);

    const frequencia = lerValor('frequencia-valor');
    criarAnel('anel-frequencia', frequencia, 100, '#0d6efd', `${frequencia}%`);

    // Gráfico: Evolução da média do aluno por trimestre (linha)
    const evolucaoEl = document.getElementById('grafico-evolucao-aluno');
    if (evolucaoEl) {
        new Chart(evolucaoEl, {
            type: 'line',
            data: {
                labels: lerLista('evolucao-aluno-labels'),
                datasets: [{
                    label: 'Média',
                    data: lerLista('evolucao-aluno-dados'),
                    borderColor: '#0d6efd',
                    backgroundColor: '#0d6efd',
                    tension: 0.3,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, max: 20 } },
            },
        });
    }

    // Gráfico: Notas do aluno por disciplina, uma barra por trimestre (mt1/mt2/mt3)
    const notasEl = document.getElementById('grafico-notas-aluno');
    if (notasEl) {
        const labels = lerLista('grafico-notas-labels');
        const mt1 = lerLista('grafico-notas-mt1');
        const mt2 = lerLista('grafico-notas-mt2');
        const mt3 = lerLista('grafico-notas-mt3');

        new Chart(notasEl, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    { label: '1º Trimestre', data: mt1, backgroundColor: '#0d6efd' },
                    { label: '2º Trimestre', data: mt2, backgroundColor: '#ffc107' },
                    { label: '3º Trimestre', data: mt3, backgroundColor: '#198754' },
                ],
            },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: true, max: 20, ticks: { precision: 0 } },
                },
                plugins: {
                    legend: { position: 'bottom' },
                },
            },
        });
    }
});
