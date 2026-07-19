document.addEventListener('DOMContentLoaded', function () {
    function lerLista(id) {
        const el = document.getElementById(id);
        return el ? JSON.parse(el.textContent) : [];
    }

    function coresPorLimite(valores, limite) {
        return valores.map((valor) => (valor < limite ? '#dc3545' : '#198754'));
    }

    const labels = lerLista('grafico-educandos-labels');

    const mediasEl = document.getElementById('grafico-medias-educandos');
    if (mediasEl) {
        const medias = lerLista('grafico-medias-dados');
        new Chart(mediasEl, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Média Geral',
                    data: medias,
                    backgroundColor: coresPorLimite(medias, 10),
                }],
            },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: true, max: 20, ticks: { precision: 0 } },
                },
                plugins: { legend: { display: false } },
            },
        });
    }

    const frequenciaEl = document.getElementById('grafico-frequencia-educandos');
    if (frequenciaEl) {
        const frequencias = lerLista('grafico-frequencia-dados');
        new Chart(frequenciaEl, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Frequência',
                    data: frequencias,
                    backgroundColor: coresPorLimite(frequencias, 75),
                }],
            },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: true, max: 100, ticks: { precision: 0 } },
                },
                plugins: { legend: { display: false } },
            },
        });
    }
});
