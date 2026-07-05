document.addEventListener('DOMContentLoaded', function () {
    const notasEl = document.getElementById('grafico-notas-aluno');

    if (notasEl) {
        const labels = JSON.parse(document.getElementById('grafico-notas-labels').textContent);
        const mt1 = JSON.parse(document.getElementById('grafico-notas-mt1').textContent);
        const mt2 = JSON.parse(document.getElementById('grafico-notas-mt2').textContent);
        const mt3 = JSON.parse(document.getElementById('grafico-notas-mt3').textContent);

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
