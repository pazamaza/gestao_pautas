document.addEventListener('DOMContentLoaded', function () {
    const cores = {
        azul: '#0d6efd',
        verde: '#198754',
        vermelho: '#dc3545',
        amarelo: '#ffc107',
        roxo: '#6f42c1',
        cinza: '#6c757d',
    };

    function lerDados(idLabels, idDados) {
        const elLabels = document.getElementById(idLabels);
        const elDados = document.getElementById(idDados);
        if (!elLabels || !elDados) {
            return null;
        }
        return {
            labels: JSON.parse(elLabels.textContent),
            dados: JSON.parse(elDados.textContent),
        };
    }

    const opcoesBase = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } } },
    };

    const evolucaoEl = document.getElementById('grafico-evolucao');
    if (evolucaoEl) {
        const { labels, dados } = lerDados('evolucao-labels', 'evolucao-dados');
        new Chart(evolucaoEl, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Média Escolar',
                    data: dados,
                    borderColor: cores.verde,
                    backgroundColor: cores.verde,
                    tension: 0.3,
                }],
            },
            options: { ...opcoesBase, scales: { y: { beginAtZero: true, max: 20 } } },
        });
    }

    const resultadosEl = document.getElementById('grafico-resultados');
    if (resultadosEl) {
        const { labels, dados } = lerDados('resultado-labels', 'resultado-dados');
        new Chart(resultadosEl, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: dados,
                    backgroundColor: [cores.verde, cores.vermelho, cores.azul, cores.amarelo, cores.roxo],
                }],
            },
            options: opcoesBase,
        });
    }

    const frequenciaEl = document.getElementById('grafico-frequencia');
    if (frequenciaEl) {
        const { labels, dados } = lerDados('frequencia-labels', 'frequencia-dados');
        new Chart(frequenciaEl, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Presença (%)',
                    data: dados,
                    borderColor: cores.azul,
                    backgroundColor: 'rgba(13, 110, 253, 0.15)',
                    fill: true,
                    tension: 0.3,
                }],
            },
            options: { ...opcoesBase, scales: { y: { beginAtZero: true, max: 100 } } },
        });
    }

    const disciplinasEl = document.getElementById('grafico-disciplinas');
    if (disciplinasEl) {
        const { labels, dados } = lerDados('disciplina-labels', 'disciplina-dados');
        new Chart(disciplinasEl, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{ label: 'Média', data: dados, backgroundColor: cores.azul }],
            },
            options: { ...opcoesBase, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 20 } } },
        });
    }

    const turmasEl = document.getElementById('grafico-turmas');
    if (turmasEl) {
        const { labels, dados } = lerDados('turma-labels', 'turma-dados');
        new Chart(turmasEl, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{ label: 'Média', data: dados, backgroundColor: cores.roxo }],
            },
            options: { ...opcoesBase, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 20 } } },
        });
    }

    const generoEl = document.getElementById('grafico-genero');
    if (generoEl) {
        const { labels, dados } = lerDados('genero-labels', 'genero-dados');
        new Chart(generoEl, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{ data: dados, backgroundColor: [cores.vermelho, cores.azul] }],
            },
            options: opcoesBase,
        });
    }
});
