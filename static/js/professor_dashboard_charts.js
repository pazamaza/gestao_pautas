document.addEventListener('DOMContentLoaded', function () {
    const mediasEl = document.getElementById('grafico-medias');
    const resultadoEl = document.getElementById('grafico-resultado');

    if (mediasEl) {
        const labels = JSON.parse(document.getElementById('grafico-medias-labels').textContent);
        const dados = JSON.parse(document.getElementById('grafico-medias-dados').textContent);

        new Chart(mediasEl, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Média (MF)',
                    data: dados,
                    backgroundColor: '#0d6efd',
                }],
            },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: true, max: 20 },
                },
                plugins: {
                    legend: { display: false },
                },
            },
        });
    }

    if (resultadoEl) {
        const labels = JSON.parse(document.getElementById('grafico-resultado-labels').textContent);
        const dados = JSON.parse(document.getElementById('grafico-resultado-dados').textContent);

        new Chart(resultadoEl, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: dados,
                    backgroundColor: ['#198754', '#dc3545'],
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
});
