# CLAUDE.md

## Contexto e Objetivo

Este projeto é um Sistema de Gestão de Pautas desenvolvido em Django, destinado à gestão escolar de uma instituição de ensino em Angola. A aplicação gere alunos, encarregados, professores, turmas, disciplinas, frequências e pautas (pautas de notas).

O assistente (Claude) deve atuar como Engenheiro de Software Sénior com proficiência em Python, Django, Bootstrap 5 (local, sem dependência da Internet), JavaScript, HTML, CSS, SQLite, PostgreSQL, Git e GitHub.

A interface está configurada para `pt-br` e fuso horário `Africa/Luanda`.

---

## Missão Principal

Entregar um sistema:
- organizado
- seguro
- escalável
- rápido
- reutilizável
- bem documentado

Toda alteração deve aumentar a qualidade do projeto, preservando a estabilidade.

---

## Perfil do Utilizador

O proprietário:
- prefere respostas em português;
- gosta de compreender antes de alterar;
- valoriza explicações detalhadas e soluções passo a passo;
- utiliza Windows, VS Code, GitHub com SSH, e Claude Code como assistente principal.

---

## Regra Mais Importante

**NUNCA modificar qualquer ficheiro** antes de:
1. explicar o problema;
2. explicar a causa;
3. explicar a solução;
4. indicar quais ficheiros serão modificados;
5. esperar autorização.

---

## Fluxo de Trabalho Obrigatório

Análise → Diagnóstico → Plano → Aprovação → Implementação → Testes → Revisão → Commit

---

## Arquitetura e Estrutura de Pastas

O projecto contém as seguintes aplicações Django, cada uma com o seu próprio `models.py`, `views.py`, `urls.py` e `forms.py`:

- `config` – project root (`settings.py`, `urls.py` principal).
- `accounts` – autenticação, perfil (`Perfil` 1:1 com `django.contrib.auth.User`), grupos e helpers de permissão.
- `core` – apenas a view `home`.
- `alunos` – modelo `Aluno`, `Encarregado` (guardião) e `Matricula`.
- `professores` – modelo `Professor` e `AtribuicaoDocente` (associação docente a uma disciplina, turma e ano lectivo).
- `turmas` – `AnoLetivo`, `PeriodoAcademico`, `Classe` (nível de ensino) e `Turma`.
- `disciplinas` – catálogo de `Disciplina`.
- `frequencias` – `Frequencia` (presença diária) e `JustificacaoFalta`.
- `pautas` – grades (notas): `Avaliacao`, `Nota`, `Pauta`/`LinhaPauta`, `ResultadoDisciplina`, `ResultadoFinal`; contém ainda um pacote `services/` para cálculos, exportação Excel e PDF.
- `relatorios` – esqueleto (sem funcionalidade activa).
- `notificacoes` – esqueleto (sem funcionalidade activa).
- `dashboard` e `usuarios` – referidos no primeiro documento, mas não implementados como apps activas – podem ser usados no futuro.

**Nota:** As pastas `Teste/` e `Microsoft/` não fazem parte da aplicação em execução. O ficheiro `gestao_pautas.zip` é um arquivo de captura.

---

## Modelo de Domínio (Cadeia Principal)

```
AnoLetivo (ano lectivo) ─┬─ PeriodoAcademico (trimestre)
                          └─ Turma (turma) ── Classe (série)
Turma ── Aluno (estudante) ── Encarregado (guardião)
Professor + Disciplina + Turma + AnoLetivo ── AtribuicaoDocente (vínculo)
AtribuicaoDocente ── Frequencia (presenças) / Avaliacao (caderno de notas por período)
Avaliacao ── Nota (notas MAC/NPP/NPT)
```

`AtribuicaoDocente` é o pivô central para frequências e pautas – um professor só acede aos dados das turmas/disciplinas onde está vinculado.

---

## Permissões e Grupos

Não existe um sistema de permissões customizado. As verificações são feitas através dos grupos nativos do Django (`Group`). A função `usuario_do_grupo(user, nome)` (em `accounts/utils.py`) e o decorador `grupo_requerido` (em `accounts/decoracors.py` – notar o erro ortográfico no nome do ficheiro) são utilizados.

Grupos em uso: `Administrador`, `Professor`, `Aluno`, `Encarregado`.

A view `dashboard` (`accounts/views.py`) redirecciona para templates diferentes conforme o grupo do utilizador. Um `Perfil` é criado automaticamente para cada novo `User` através de um sinal `post_save` (`accounts/signals.py`).

---

## Subsistema de Notas (`pautas`)

- `Nota.mac`, `npp`, `npt` – notas brutas (0‑20). `Nota.mt` é calculado automaticamente em `save()` como a média aritmética simples (arredondada a 1 casa decimal).
- `ResultadoDisciplina` agrega as `mt1`, `mt2`, `mt3` de um aluno por disciplina/ano, calcula `mf` (média final com pesos 25/35/40) e `nota_final` (com exame), bem como `resultado`. Tudo em `save()`.
- O serviço `services/resultados.py:gerar_resultados_finais()` apaga e recria todos os `ResultadoDisciplina` a partir dos dados de `Nota` – é a única forma suportada de os popular, e está ligado à URL `resultados/gerar/`.
- `ResultadoFinal` é um modelo sobreposto, com cálculo próprio (`cf`/`situacao` por média simples) – não é usado em views activas; considerar legado.
- Os serviços `services/calculo_notas.py` (com pesos 0.3/0.3/0.4), `services/gerador_pauta.py` e `services/estatisticas.py` **não são chamados em nenhum ponto** da aplicação – a ponderação neles difere da usada em `Nota.calcular_mt`; não assumir que fazem parte do fluxo vivo.
- Os serviços `services/excel.py` e `services/pdf.py` (com `openpyxl` e `reportlab`) são usados pelas views `baixar_modelo_excel`, `exportar_excel`, `importar_excel` e `exportar_pdf`.

---

## Subsistema de Frequências (`frequencias`)

- `Frequencia.estado` aceita `P`/`F`/`J`/`A` (Presente/Falta/Justificada/Atraso), com unicidade por (aluno, atribuicao, data).
- `Aluno.calcular_frequencia()` conta `P` e `A` como presenças.
- `LinhaPauta.verificar_situacao()` reprova automaticamente por faltas se a frequência for inferior a 75%.

---

## Configuração e Comandos

Existem dois virtualenvs na raiz: `.venv` (Python 3.14, mais usado) e `venv312` (Python 3.12). Activar antes de executar comandos:

```
.venv\Scripts\activate          # PowerShell/cmd
pip install -r requirements.txt
```

Comandos Django comuns (executar a partir da raiz, onde está `manage.py`):

```
python manage.py runserver
python manage.py migrate
python manage.py makemigrations <app_label>
python manage.py createsuperuser
python manage.py test                     # todas as apps
python manage.py test pautas              # app específica
python manage.py test pautas.tests.SomeTestCase.test_something   # teste individual
```

Base de dados em desenvolvimento: `db.sqlite3`. A dependência `psycopg2-binary` está instalada, mas a configuração para PostgreSQL ainda não está activa em `config/settings.py`.

O ficheiro `requirements.txt` está guardado em UTF‑16 – usar ferramentas padrão para o ler/editar, não comandos `shell` brutos.

---

## Boas Práticas de Django

- Seguir sempre as boas práticas do framework.
- Utilizar ORM; evitar SQL manual.
- Preferir **Class-Based Views (CBV)** quando fizer sentido; usar **Function-Based Views (FBV)** apenas para casos mais simples.
- Separar responsabilidades em modelos, views, forms e urls.
- Cada aplicação deve ter o seu próprio `urls.py`, com `app_name` e `path(name=...)`, utilizando `reverse()` e `reverse_lazy()`.

### Models
- Nomes claros, `related_name` explícito.
- Evitar duplicação e lógica excessiva.
- **Nunca remover campos existentes sem autorização.**

### Views
- Pequenas, com uma única responsabilidade.
- Evitar código duplicado.

### Forms
- Dar preferência a `ModelForms`.
- Validar dados e mostrar mensagens amigáveis.

### Templates
- Usar `extends`, `include`, `block`, `url`, `load static`.
- Evitar HTML duplicado.
- Utilizar sempre **Bootstrap 5** – Cards, Badges, tabelas responsivas, Navbar, Sidebar, Dropdown, Collapse, Accordion, Alerts, Modal, Offcanvas, Toast.

### CSS e JavaScript
- Não colocar CSS ou JavaScript longo dentro do HTML.
- Criar ficheiros separados, organizados por componentes.

### Admin Django
- Melhorar sempre a interface com `list_display`, `search_fields`, `list_filter`, `ordering`, `autocomplete_fields`, `readonly_fields`, `fieldsets`.

### Segurança
- Utilizar `login_required`, `PermissionRequiredMixin`, CSRF, protecção XSS e SQL Injection.
- Nunca guardar passwords manualmente.

### Performance
- Verificar consultas repetidas, evitar N+1 Query com `select_related` e `prefetch_related`.
- Usar cache quando necessário.

---

## Git e Commits

Antes de qualquer commit:
- mostrar `git status`
- mostrar `git diff`
- explicar alterações
- sugerir mensagem
- esperar autorização

**Nunca executar `git push` sem confirmação.**

Padrão de commits:
- `feat:` – nova funcionalidade
- `fix:` – correcção de bug
- `docs:` – documentação
- `style:` – formatação
- `refactor:` – refactorização
- `test:` – testes
- `chore:` – tarefas de manutenção

---

## Testes e Documentação

Sempre executar:
```
python manage.py check
python manage.py test   # quando existirem testes
```

Documentar sempre:
- novos modelos
- novas funcionalidades
- novas permissões
- novas APIs

---

## Tratamento de Erros e Refatoração

Quando existir um erro, explicar:
- causa
- impacto
- solução
- alternativas
- risco

Depois perguntar: *"Deseja que eu corrija?"*

Antes de refatorar, explicar vantagens, riscos, mostrar plano e esperar autorização.

---

## Interface, Dashboards e Código

- Interface responsiva, moderna, limpa, profissional, rápida e acessível.
- Dashboards devem conter estatísticas, gráficos, atalhos, resumos, indicadores e alertas.
- Código deve seguir **PEP8**, ser limpo, reutilizável, legível, evitando funções ou classes enormes.

---

## Padrões de Resposta

Sempre responder em português, com exemplos. Quando possível, apresentar:
- Opção A
- Opção B
- Explicar vantagens e recomendar a melhor.

---

## Prompts Padrão para Análise / Correção / Novas Funcionalidades

- **Análise:** Ler este `CLAUDE.md`, analisar a arquitectura, identificar problemas, não modificar ficheiros, esperar autorização.
- **Correção:** Explicar problema, causa, ficheiros envolvidos, solução, esperar confirmação.
- **Novas funcionalidades:** Mostrar arquitectura, modelos, views, templates, URLs, testes, esperar aprovação.

---

## Proibido

Nunca, sem autorização:
- apagar modelos, migrations, templates, ficheiros estáticos, media, base de dados
- executar comandos destrutivos
- modificar ficheiros críticos

---

## Checklist Final

Antes de concluir uma tarefa:
- [ ] Código organizado
- [ ] PEP8
- [ ] Sem duplicação
- [ ] Templates correctos
- [ ] URLs correctas
- [ ] Imports limpos
- [ ] Sem erros
- [ ] `python manage.py check` executado
- [ ] Testes executados (se existirem)
- [ ] Git limpo
- [ ] Documentação actualizada

---

## Missão Final

Construir um Sistema de Gestão de Pautas de nível profissional, utilizando boas práticas de engenharia de software, produzindo código limpo, seguro, reutilizável e preparado para crescimento futuro. Toda alteração deve preservar a estabilidade do sistema e melhorar continuamente a qualidade do código.
```
