document.addEventListener('DOMContentLoaded', function () {
    const estadosEl = document.getElementById('grafico-estados');
    const turmasEl = document.getElementById('grafico-turmas');

    if (estadosEl) {
        const labels = JSON.parse(document.getElementById('estados-labels').textContent);
        const dados = JSON.parse(document.getElementById('estados-dados').textContent);

        new Chart(estadosEl, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: dados,
                    backgroundColor: ['#198754', '#dc3545', '#0d6efd'],
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
        const labels = JSON.parse(document.getElementById('turma-labels').textContent);
        const presentes = JSON.parse(document.getElementById('turma-presentes').textContent);
        const ausentes = JSON.parse(document.getElementById('turma-ausentes').textContent);
        const justificadas = JSON.parse(document.getElementById('turma-justificadas').textContent);

        new Chart(turmasEl, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Presentes', data: presentes, backgroundColor: '#198754' },
                    { label: 'Ausentes', data: ausentes, backgroundColor: '#dc3545' },
                    { label: 'Justificadas', data: justificadas, backgroundColor: '#0d6efd' },
                ],
            },
            options: {
                responsive: true,
                scales: {
                    x: { stacked: true },
                    y: { stacked: true, beginAtZero: true },
                },
                plugins: {
                    legend: { position: 'bottom' },
                },
            },
        });
    }
});
