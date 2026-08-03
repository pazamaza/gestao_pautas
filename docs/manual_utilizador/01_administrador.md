# Manual do Administrador

[← Voltar ao índice](00_indice.md)

O Administrador tem acesso total ao sistema: configura a estrutura da escola
(turmas, disciplinas, professores, atribuições), acompanha e valida as
pautas, gera os resultados finais e decide os pedidos de documentos.

> **Importante:** boa parte das ações do Administrador não está no menu do
> topo, mas sim em **atalhos e cartões dentro do próprio Painel**. Este
> manual indica sempre onde clicar exatamente.

## Painel (Dashboard)

Ao entrar, o Administrador vê:

- Totais de alunos, professores, turmas, disciplinas e encarregados ativos;
- Média geral, taxa de aprovação/reprovação do ano letivo selecionado
  (pode escolher o ano no topo do painel);
- Gráficos: evolução trimestral da média, distribuição de resultados,
  médias por disciplina, ranking de turmas, distribuição por género,
  frequência mensal;
- Listas de atalho: alunos em risco (média baixa) e melhores médias;
- **Atalhos Rápidos**: botões para Estudantes, Professores, Turmas,
  Encarregados;
- **Validação de Pautas**: cartões clicáveis — Trimestrais Pendentes, Com
  Erros, Validadas, e Resultados Anuais Validados;
- **Boletins e Certificados**: cartões clicáveis — Pedidos Pendentes de
  Autorização, Pagamentos por Confirmar;
- **Período de Lançamento de Notas**: tabela dos períodos com botão
  **Gerir Períodos**.

## Menu do topo

- **Painel Admin**: acesso direto ao Django Admin (`/admin/`) — usado para
  criar contas de Aluno (ver abaixo) e para operações avançadas de base de
  dados.
- **Cadastros**: Estudantes, Professores, Turmas, Diretores de Turma,
  Períodos de Lançamento, Atribuições Docentes, Frequências.
- **Pautas**: Pautas Finais, Mini-Pauta Trimestral.
- **Notificações** e **Sair**.

(Disciplinas e Encarregados não estão no menu do topo — ver abaixo onde
aceder.)

## Cadastros (estrutura da escola)

### Alunos
Menu **Cadastros → Estudantes** (ou atalho "Estudantes" no Painel).
- **Listar/pesquisar**, **Novo aluno**, **Editar**, **Excluir**.

#### Dar acesso a um Aluno

Por predefinição, um aluno é criado **sem** conta de acesso. Para lhe dar
login:

1. **Painel Admin** (`/admin/`) → **Contas de Aluno** → *Adicionar* — cria
   o utilizador (username/password) e já fica automaticamente no grupo
   "Aluno".
2. Volte à ficha do aluno em **Cadastros → Estudantes → Editar** e associe
   o utilizador criado no campo de conta de acesso.

### Professores
Menu **Cadastros → Professores** (ou atalho "Professores" no Painel).
- **Novo professor**: um único formulário cria a conta de acesso (grupo
  "Professor" atribuído automaticamente) e a ficha profissional.
- **Editar / Excluir** a partir da lista.

### Encarregados
Atalho **"Encarregados"** no Painel (não está no menu do topo). Na lista,
o botão **Novo** cria a conta de acesso (grupo "Encarregado") junto com os
dados do encarregado.

### Turmas
Menu **Cadastros → Turmas** (ou atalho "Turmas" no Painel).
- **Nova turma**, **Editar**, **Desativar/Reativar**, **Turmas inativas**.

### Disciplinas
Sem atalho no menu nem no Painel — aceda diretamente pelo endereço
`/disciplinas/` para listar/criar/editar disciplinas, ou faça a gestão pelo
**Painel Admin**.

### Diretores de Turma
Menu **Cadastros → Diretores de Turma**.
- **Nomear diretor de turma**: associa um professor como responsável por
  uma turma/ano letivo — dá-lhe acesso à Pauta Final da turma e à
  aprovação de pedidos de Boletim dessa turma.

### Períodos de Lançamento
Menu **Cadastros → Períodos de Lançamento** (ou botão **Gerir Períodos**
no Painel).
- Define os 3 trimestres do ano letivo e controla se o **lançamento de
  notas está aberto ou fechado** em cada um.

### Atribuições Docentes
Menu **Cadastros → Atribuições Docentes**.
- Liga um **Professor** a uma **Disciplina** numa **Turma**, num **Ano
  Letivo**. É esta ligação que dá ao professor acesso ao lançamento de
  notas e frequências dessa turma/disciplina.

## Validar Pautas e Resultados

A partir dos cartões **Validação de Pautas** no Painel (ou de
**Pautas → Pautas Finais** / **Mini-Pauta Trimestral** no menu):

1. **Trimestrais Pendentes / Com Erros / Validadas**: abre a lista de
   avaliações (pautas trimestrais) nesse estado.
   - Dentro de uma avaliação (**Pauta Trimestral**): **Validar** liberta
     as notas para alunos/encarregados verem; **Reportar Erro** devolve a
     pauta ao professor com uma observação (notifica automaticamente o
     professor e o diretor de turma).
   - **Modelo Excel / Exportar Excel / Exportar PDF** disponíveis na
     mesma página, para imprimir ou distribuir a pauta.
2. **Resultados Anuais Validados**: abre a lista de resultados por
   disciplina (`Resultado por Disciplina`), com **Validar** / **Reportar
   Erro** — mesma lógica das avaliações.
3. **Pautas Finais** (menu): vista consolidada de todas as disciplinas e
   a situação anual de cada aluno de uma turma, com exportação em PDF.
4. **Mini-Pauta Trimestral** (menu): pauta de apoio por disciplina/turma,
   com exportação Excel/PDF.

### Gerar Resultados Finais

Recalcula, para **todos** os alunos, o resultado final por disciplina (MF
e situação: Aprovado/Reprovado/Exame) a partir de todas as notas
lançadas. **Não tem botão na interface** — aceda diretamente ao endereço
`/pautas/resultados/gerar/`. Corra esta operação só depois de todas as
pautas do 3º trimestre estarem validadas, para evitar recálculos
parciais.

> **Nota:** criar/editar/excluir um resultado manualmente é restrito ao
> superutilizador — use apenas em situações excecionais; o caminho normal
> é sempre **Gerar Resultados Finais**.

## Documentos — Boletim e Certificado

A partir dos cartões **Boletins e Certificados** no Painel. Fluxo de um
pedido:

```
pendente → autorizado → pagamento submetido → pronto para levantamento → levantado
                 (pode ser "recusado" em qualquer ponto antes de autorizado)
```

1. **Pedidos Pendentes de Autorização**: o aluno solicita, e aqui o
   Administrador **autoriza** ou **recusa** (com motivo) o pedido.
   Certificados só podem ser decididos pelo Administrador; Boletins também
   podem ser decididos pelo Diretor de Turma do aluno.
2. **Pagamentos por Confirmar**: depois de autorizado, o aluno carrega um
   comprovativo de pagamento — aqui o Administrador **confirma o
   pagamento** (avança para "Pronto para Levantamento") ou **rejeita o
   comprovativo** (pede reenvio).
3. **Marcar como levantado**: quando o aluno/encarregado levanta o
   documento fisicamente (botão na página do pedido).
4. **Emitir PDF**: disponível assim que o pedido estiver "Pronto" ou
   "Levantado".

Em cada mudança de estado, o aluno é notificado automaticamente (sino de
notificações).

## Frequência

Menu **Cadastros → Frequências** — visão de todas as turmas, com filtros
de data/turma/mês; a partir daí também é possível **lançar frequência**
em qualquer turma/aula.

- **Relatório de Assiduidade** e **Justificações de Falta** (aprovação):
  sem atalho no menu para o Administrador — aceda diretamente a
  `/frequencias/relatorios/` e `/frequencias/justificacoes/`.

## Boas práticas

- Confirme que o **Período de Lançamento** do trimestre em curso está
  aberto antes de os professores começarem a lançar notas, e feche-o
  quando terminar o prazo.
- Valide as avaliações regularmente — os alunos só veem notas depois de
  validadas.
- Corra **Gerar Resultados Finais** só depois de todas as pautas do 3º
  trimestre estarem validadas.
