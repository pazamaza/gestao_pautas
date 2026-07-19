(function () {
    'use strict';

    function arredondar(valor) {
        return Math.round(valor * 10) / 10;
    }

    function paraNumero(valor) {
        if (valor === null || valor === undefined || valor === '') return null;
        const numero = parseFloat(valor);
        return isNaN(numero) ? null : numero;
    }

    function calcularMt(mac, npt) {
        if (mac === null || npt === null) return null;
        return arredondar((mac + npt) / 2);
    }

    function iniciarTabelaNotas() {
        const tabela = document.querySelector('[data-notas-tabela]');
        if (!tabela) return;

        const terceiroTrimestre = tabela.dataset.terceiroTrimestre === 'true';

        function atualizarLinha(tr) {
            const macInput = tr.querySelector('[data-campo="mac"]');
            const nptInput = tr.querySelector('[data-campo="npt"]');
            const mtCelula = tr.querySelector('[data-campo="mt"]');
            if (!macInput || !nptInput || !mtCelula) return;

            const mac = paraNumero(macInput.value);
            let npt;

            if (terceiroTrimestre) {
                const mt1 = paraNumero(tr.dataset.mt1);
                const mt2 = paraNumero(tr.dataset.mt2);
                npt = (mt1 !== null && mt2 !== null) ? arredondar((mt1 + mt2) / 2) : null;
                nptInput.value = npt !== null ? npt.toFixed(1) : '';
                nptInput.readOnly = true;
                nptInput.classList.add('bg-light');
            } else {
                npt = paraNumero(nptInput.value);
            }

            const mt = calcularMt(mac, npt);
            mtCelula.textContent = mt !== null ? mt.toFixed(1) : '—';
            mtCelula.classList.toggle('text-danger', mt !== null && mt < 10);
            mtCelula.classList.toggle('text-success', mt !== null && mt >= 10);
        }

        tabela.querySelectorAll('tbody tr[data-linha]').forEach(function (tr) {
            atualizarLinha(tr);
            tr.querySelectorAll('[data-campo="mac"], [data-campo="npt"]').forEach(function (input) {
                input.addEventListener('input', function () { atualizarLinha(tr); });
            });
        });
    }

    function mostrarResultado(elemento, texto, tipo) {
        elemento.textContent = texto;
        elemento.classList.remove('d-none', 'alert-info', 'alert-danger');
        elemento.classList.add(tipo === 'erro' ? 'alert-danger' : 'alert-info');
    }

    function iniciarCalculadora() {
        const btnNota = document.getElementById('calcNotaNecessariaBtn');
        if (btnNota) {
            btnNota.addEventListener('click', function () {
                const resultado = document.getElementById('calcNotaNecessariaResultado');
                const mac = paraNumero(document.getElementById('calcMac').value);
                const npt = paraNumero(document.getElementById('calcNpt').value);
                const mtDesejada = paraNumero(document.getElementById('calcMtDesejada').value);

                const preenchidos = [mac, npt].filter(function (v) { return v !== null; }).length;

                if (mtDesejada === null || preenchidos !== 1) {
                    mostrarResultado(
                        resultado,
                        'Preenche a média desejada e exatamente um dos campos (MAC ou NPT) — o outro será calculado.',
                        'erro'
                    );
                    return;
                }

                if (mac === null) {
                    const macNecessario = arredondar(2 * mtDesejada - npt);
                    mostrarResultado(resultado, 'Precisa de MAC = ' + macNecessario.toFixed(1) + ' para atingir a média ' + mtDesejada.toFixed(1) + '.', 'info');
                } else {
                    const nptNecessario = arredondar(2 * mtDesejada - mac);
                    mostrarResultado(resultado, 'Precisa de NPT = ' + nptNecessario.toFixed(1) + ' para atingir a média ' + mtDesejada.toFixed(1) + '.', 'info');
                }
            });
        }

        const btnFrequencia = document.getElementById('calcFrequenciaBtn');
        if (btnFrequencia) {
            btnFrequencia.addEventListener('click', function () {
                const resultado = document.getElementById('calcFrequenciaResultado');
                const presencas = paraNumero(document.getElementById('calcPresencas').value);
                const total = paraNumero(document.getElementById('calcTotalAulas').value);

                if (presencas === null || total === null || total <= 0 || presencas > total) {
                    mostrarResultado(resultado, 'Indica um número de presenças válido e um total de aulas maior que zero.', 'erro');
                    return;
                }

                const percentagem = arredondar((presencas / total) * 100);
                const situacao = percentagem < 75
                    ? 'Reprovado por Faltas (abaixo dos 75%)'
                    : 'Frequência regular (75% ou mais)';
                mostrarResultado(resultado, percentagem.toFixed(1) + '% de frequência — ' + situacao, percentagem < 75 ? 'erro' : 'info');
            });
        }

        const btnLivre = document.getElementById('calcLivreBtn');
        if (btnLivre) {
            btnLivre.addEventListener('click', function () {
                const resultado = document.getElementById('calcLivreResultado');
                const expressao = document.getElementById('calcLivreExpressao').value.trim();

                if (!/^[0-9+\-*/.,\s()]+$/.test(expressao) || expressao === '') {
                    mostrarResultado(resultado, 'Usa apenas números e os operadores + - * / ( )', 'erro');
                    return;
                }

                try {
                    const valor = Function('"use strict"; return (' + expressao.replace(/,/g, '.') + ')')();
                    if (typeof valor !== 'number' || !isFinite(valor)) throw new Error('inválido');
                    mostrarResultado(resultado, '= ' + arredondar(valor).toFixed(1), 'info');
                } catch (erro) {
                    mostrarResultado(resultado, 'Expressão inválida.', 'erro');
                }
            });
        }

        const btnMedia = document.getElementById('calcMediaValoresBtn');
        if (btnMedia) {
            btnMedia.addEventListener('click', function () {
                const resultado = document.getElementById('calcMediaValoresResultado');
                const valores = document.getElementById('calcMediaValores').value
                    .split(',')
                    .map(function (v) { return paraNumero(v.trim()); });

                if (valores.some(function (v) { return v === null; }) || valores.length === 0) {
                    mostrarResultado(resultado, 'Indica valores numéricos separados por vírgula (ex.: 12,15,18).', 'erro');
                    return;
                }

                const soma = valores.reduce(function (acumulado, v) { return acumulado + v; }, 0);
                const media = arredondar(soma / valores.length);
                mostrarResultado(resultado, 'Média de ' + valores.length + ' valor(es) = ' + media.toFixed(1), 'info');
            });
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        iniciarTabelaNotas();
        iniciarCalculadora();
    });
})();
