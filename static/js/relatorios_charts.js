document.addEventListener('DOMContentLoaded', function () {
    const evolucaoEl = document.getElementById('grafico-evolucao');
    const disciplinasEl = document.getElementById('grafico-disciplinas');

    if (evolucaoEl) {
        const labels = JSON.parse(document.getElementById('evolucao-labels').textContent);
        const dados = JSON.parse(document.getElementById('evolucao-dados').textContent);

        new Chart(evolucaoEl, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Média (MT)',
                    data: dados,
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.15)',
                    fill: true,
                    tension: 0.3,
                }],
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true, max: 20 } },
                plugins: { legend: { display: false } },
            },
        });
    }

    if (disciplinasEl) {
        const labels = JSON.parse(document.getElementById('disciplinas-labels').textContent);
        const dados = JSON.parse(document.getElementById('disciplinas-dados').textContent);

        new Chart(disciplinasEl, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Média (MF)',
                    data: dados,
                    backgroundColor: '#6f42c1',
                }],
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true, max: 20 } },
                plugins: { legend: { display: false } },
            },
        });
    }
});
