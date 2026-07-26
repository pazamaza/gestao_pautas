document.addEventListener('DOMContentLoaded', function () {
    function lerJson(id) {
        const elemento = document.getElementById(id);
        return elemento ? JSON.parse(elemento.textContent) : null;
    }

    const faixasLabels = lerJson('faixas-labels');
    if (!faixasLabels) return; // sem resumo (ainda não há resultados) — nada a desenhar

    const CORES_FAIXAS = ['#dc3545', '#fd7e14', '#8bc34a', '#4caf50', '#0d6efd'];

    function desenharDonut(elementoId, dados) {
        const elemento = document.getElementById(elementoId);
        if (!elemento || !dados) return;

        new Chart(elemento, {
            type: 'doughnut',
            data: {
                labels: faixasLabels,
                datasets: [{
                    data: dados,
                    backgroundColor: CORES_FAIXAS,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 9 } } },
                },
            },
        });
    }

    desenharDonut('donut-trimestre-1', lerJson('distrib-t1'));
    desenharDonut('donut-trimestre-2', lerJson('distrib-t2'));
    desenharDonut('donut-trimestre-3', lerJson('distrib-t3'));
    desenharDonut('donut-final', lerJson('distrib-final'));

    const evolucaoEl = document.getElementById('grafico-evolucao');
    if (evolucaoEl) {
        new Chart(evolucaoEl, {
            type: 'line',
            data: {
                labels: lerJson('evolucao-labels'),
                datasets: [{
                    label: 'Média da Turma',
                    data: lerJson('evolucao-medias'),
                    borderColor: '#198754',
                    backgroundColor: 'rgba(25, 135, 84, 0.15)',
                    fill: true,
                    tension: 0.3,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true, max: 20 } },
                plugins: { legend: { display: false } },
            },
        });
    }

    const taxaEl = document.getElementById('grafico-taxa-aprovacao');
    if (taxaEl) {
        new Chart(taxaEl, {
            type: 'bar',
            data: {
                labels: lerJson('evolucao-labels'),
                datasets: [{
                    label: 'Taxa de Aprovação (%)',
                    data: lerJson('evolucao-taxas'),
                    backgroundColor: ['#0d6efd', '#8bc34a', '#fd7e14'],
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true, max: 100 } },
                plugins: { legend: { display: false } },
            },
        });
    }
});
