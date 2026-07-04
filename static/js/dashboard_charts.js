document.addEventListener('DOMContentLoaded', function () {
    const avaliacoesEl = document.getElementById('grafico-avaliacoes');
    const turmasEl = document.getElementById('grafico-turmas');

    if (avaliacoesEl) {
        const labels = JSON.parse(document.getElementById('grafico-avaliacoes-labels').textContent);
        const dados = JSON.parse(document.getElementById('grafico-avaliacoes-dados').textContent);

        new Chart(avaliacoesEl, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: dados,
                    backgroundColor: ['#6c757d', '#ffc107', '#198754'],
                }],
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' },
                },
            },
        });
    }

    if (turmasEl) {
        const labels = JSON.parse(document.getElementById('grafico-turmas-labels').textContent);
        const dados = JSON.parse(document.getElementById('grafico-turmas-dados').textContent);

        new Chart(turmasEl, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Turmas ativas',
                    data: dados,
                    backgroundColor: '#0d6efd',
                }],
            },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } },
                },
                plugins: {
                    legend: { display: false },
                },
            },
        });
    }
});
