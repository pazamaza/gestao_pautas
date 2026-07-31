(function () {
    'use strict';

    function arredondar(valor) {
        // "Base Legal": arredondamento à unidade mais próxima (ex.: 13,5 -> 14) —
        // preview visual; o cálculo oficial acontece no servidor.
        return Math.round(valor);
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

    function calcularMtComExame(mac, ne) {
        // IIº Ano EJA, 3º trimestre: MT = MAC×0,40 + NE×0,60 (ver
        // Nota.calcular_mt_com_exame em pautas/models.py).
        if (mac === null || ne === null) return null;
        return arredondar((mac * 0.40) + (ne * 0.60));
    }

    function iniciarTabelaNotas() {
        const tabela = document.querySelector('[data-notas-tabela]');
        if (!tabela) return;

        const terceiroTrimestre = tabela.dataset.terceiroTrimestre === 'true';
        const formulaRecurso = tabela.dataset.formulaRecurso === 'true';

        // Recalcula a coluna MT ao vivo (client-side) sempre que MAC/NPT
        // mudam. Os '[data-campo="..."]' são atribuídos no template
        // (templates/pautas/lancamento_notas.html) e correspondem aos
        // mesmos nomes de campo usados em pautas/forms.py (NotaForm) — é só
        // um preview visual, a gravação real e o cálculo oficial de MT
        // acontecem no servidor, em Nota.calcular_mt() (pautas/models.py).
        function atualizarLinha(tr) {
            const macInput = tr.querySelector('[data-campo="mac"]');
            const nptInput = tr.querySelector('[data-campo="npt"]');
            const mtCelula = tr.querySelector('[data-campo="mt"]');
            const mfaCelula = tr.querySelector('[data-campo="mfa"]');
            if (!macInput || !nptInput || !mtCelula) return;

            const mac = paraNumero(macInput.value);
            let npt;
            let mt;

            if (formulaRecurso) {
                // IIº Ano EJA, 3º trimestre: o campo (rotulado "NE" no
                // template) continua editável pelo professor, tal como o
                // MAC — só muda a fórmula do MT, que pondera os dois
                // (40%/60%) em vez de fazer a média simples.
                npt = paraNumero(nptInput.value);
                mt = calcularMtComExame(mac, npt);
            } else if (terceiroTrimestre) {
                // Mesma regra do 3º trimestre implementada no servidor
                // (Nota.calcular_npt_terceiro_trimestre): o NPT não é
                // editável — é a média de mt1/mt2, injectados no HTML via
                // tr.dataset.mt1/mt2 (data-mt1/data-mt2 no template).
                const mt1 = paraNumero(tr.dataset.mt1);
                const mt2 = paraNumero(tr.dataset.mt2);
                npt = (mt1 !== null && mt2 !== null) ? arredondar((mt1 + mt2) / 2) : null;
                nptInput.value = npt !== null ? npt.toFixed(0) : '';
                nptInput.readOnly = true;
                nptInput.classList.add('bg-light');
                mt = calcularMt(mac, npt);
            } else {
                npt = paraNumero(nptInput.value);
                mt = calcularMt(mac, npt);
            }

            mtCelula.textContent = mt !== null ? mt.toFixed(0) : '—';
            mtCelula.classList.toggle('text-danger', mt !== null && mt < 10);
            mtCelula.classList.toggle('text-success', mt !== null && mt >= 10);

            if (mfaCelula) {
                // MFA (média anual = média de mt1/mt2/MT deste trimestre) —
                // é este valor, não o MT isolado do 3º trimestre, que decide
                // Aprovado/Recurso/Reprovado (ver ResultadoDisciplina.
                // _verificar_resultado_segundo_ano, pautas/models.py).
                const mt1 = paraNumero(tr.dataset.mt1);
                const mt2 = paraNumero(tr.dataset.mt2);
                const mfa = (mt1 !== null && mt2 !== null && mt !== null)
                    ? arredondar((mt1 + mt2 + mt) / 3)
                    : null;
                mfaCelula.textContent = mfa !== null ? mfa.toFixed(0) : '—';
                mfaCelula.classList.toggle('text-danger', mfa !== null && mfa <= 6);
                mfaCelula.classList.toggle('text-warning', mfa !== null && mfa >= 7 && mfa <= 9);
                mfaCelula.classList.toggle('text-success', mfa !== null && mfa >= 10);
            }
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

                // Calculadora livre: avalia uma expressão aritmética digitada
                // pelo utilizador. Usa Function(...) em vez de eval() directo
                // porque cria um novo escopo isolado (sem acesso às variáveis
                // locais desta função) — mas só é seguro porque a regex acima
                // já rejeitou tudo o que não seja dígito, '.', ',', espaço ou
                // um dos operadores +-*/(); não há forma de injectar código.
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
