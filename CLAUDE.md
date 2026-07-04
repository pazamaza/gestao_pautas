# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Django app for managing school records ("Gestão de Pautas") for an Angolan school: students
(`alunos`), guardians (`Encarregado`), teachers (`professores`), classes (`turmas`), subjects
(`disciplinas`), attendance (`frequencias`), and grade sheets/report cards (`pautas`). UI language
is `pt-br` (`config/settings.py`), timezone is `Africa/Luanda`.

## Setup & commands

Two virtualenvs exist at the repo root: `.venv` (Python 3.14, most recently used) and `venv312`
(Python 3.12). Activate whichever is current before running commands:

```
.venv\Scripts\activate          # PowerShell/cmd
pip install -r requirements.txt
```

Common Django commands (run from the repo root, where `manage.py` lives):

```
python manage.py runserver
python manage.py migrate
python manage.py makemigrations <app_label>
python manage.py createsuperuser
python manage.py test                     # all apps
python manage.py test pautas              # single app
python manage.py test pautas.tests.SomeTestCase.test_something   # single test
```

There is no configured linter/formatter in this repo — don't assume Black/flake8/ruff config exists.

Database is SQLite (`db.sqlite3`) in dev; `psycopg2-binary` is a dependency but no Postgres
settings are wired up in `config/settings.py`.

`requirements.txt` is saved as UTF-16; use the standard file tools rather than raw shell text
tools when reading/editing it.

## Architecture

### Apps

`config` is the project package (`settings.py`, root `urls.py`). Feature apps, each with its own
`models.py`/`views.py`/`urls.py`/`forms.py`:

- `accounts` — auth glue: `Perfil` (1:1 profile extending `django.contrib.auth.User`), role
  helpers, login/logout/dashboard views.
- `alunos` — `Aluno` (student) and `Encarregado` (guardian), plus `Matricula` (enrollment record).
- `professores` — `Professor` and `AtribuicaoDocente` (a teacher's assignment to a
  subject+class+school-year — the join model that `frequencias` and `pautas` hang off of).
- `turmas` — `AnoLetivo` (school year), `PeriodoAcademico` (term), `Classe` (grade level), `Turma`
  (class/section).
- `disciplinas` — `Disciplina` (subject catalog).
- `frequencias` — `Frequencia` (daily attendance per student per `AtribuicaoDocente`) and
  `JustificacaoFalta` (absence justification).
- `pautas` — grades: `Avaliacao`, `Nota`, `Pauta`/`LinhaPauta`, `ResultadoDisciplina`,
  `ResultadoFinal` (see below). Has a `services/` package for calculations, Excel and PDF export.
- `core` — just the `home` view/URL.
- `relatorios`, `notificacoes` — scaffolded (`startapp` boilerplate only: empty models/views), not
  wired into `config/urls.py`. Don't assume functionality exists here.

Two other top-level folders are **not** part of the running app: `Teste/` is an older full copy of
the project (its own venv, own db) kept for reference/testing — don't edit it expecting changes to
affect the real app. `Microsoft/` is unrelated OS/OneDrive content that ended up in this directory.
`gestao_pautas.zip` is a snapshot archive.

### Domain model chain

```
AnoLetivo (school year) ─┬─ PeriodoAcademico (term)
                          └─ Turma (class) ── Classe (grade level)
Turma ── Aluno (student) ── Encarregado (guardian)
Professor + Disciplina + Turma + AnoLetivo ── AtribuicaoDocente (teaching assignment)
AtribuicaoDocente ── Frequencia (attendance) / Avaliacao (per-term gradebook)
Avaliacao ── Nota (a student's MAC/NPP/NPT scores for that gradebook)
```

`AtribuicaoDocente` is the pivot almost everything else in `frequencias` and `pautas` joins
through — a teacher only has access to attendance/grades via their assignments to a specific
class+subject+year.

### Roles & permissions

There's no custom permission framework — role checks are done via Django's built-in `Group` model:
`accounts/utils.py:usuario_do_grupo(user, nome)` checks group membership, and
`accounts/decoracors.py:grupo_requerido(nome)` (note the filename typo — not `decorators.py`) is a
`user_passes_test` decorator wrapper for it. Groups in use: `Administrador`, `Professor`, `Aluno`,
`Encarregado`. `accounts/views.py:dashboard` branches on `is_superuser` then group membership to
pick which `templates/dashboards/*.html` to render. A `Perfil` is auto-created for every new `User`
via a `post_save` signal (`accounts/signals.py`, wired in `accounts/apps.py:AccountsConfig.ready`).

### Grades (`pautas`) subsystem

- `Nota.mac/npp/npt` are raw scores (0–20); `Nota.mt` is auto-computed in `save()` as their
  unweighted average, rounded half-up to 1 decimal.
- `ResultadoDisciplina` aggregates a student's `mt1/mt2/mt3` per subject/year and computes `mf`
  (weighted 25/35/40), `nota_final` (with exam) and `resultado`, all in `save()`.
  `services/resultados.py:gerar_resultados_finais()` rebuilds all `ResultadoDisciplina` rows from
  `Nota` data (deletes and regenerates) and is the only supported way to populate them — it's
  wired to the `resultados/gerar/` URL.
- `ResultadoFinal` is a separate, overlapping model with its own `cf`/`situacao` calculation
  (simple average, no weighting) — nothing in `views.py` creates/uses it; treat it as legacy/dead
  unless you find a caller.
- `services/calculo_notas.py` (`calcular_mt`, weighted 0.3/0.3/0.4) and
  `services/gerador_pauta.py`/`services/estatisticas.py` are **not called from anywhere** in the
  app (only self-referenced) — don't assume they're part of a live code path; the weighting there
  also disagrees with `Nota.calcular_mt`'s unweighted average.
- `services/excel.py` / `services/pdf.py` handle the openpyxl/reportlab import-export flows used by
  `pautas/views.py` (`baixar_modelo_excel`, `exportar_excel`, `importar_excel`, `exportar_pdf`).

### Attendance (`frequencias`)

`Frequencia.estado` is one of `P`/`F`/`J`/`A` (Presente/Falta/Justificada/Atraso), unique per
(aluno, atribuicao, data). `Aluno.calcular_frequencia()` computes attendance % counting `P`/`A` as
present; `pautas/models.py:LinhaPauta.verificar_situacao()` fails a student below 75% attendance
regardless of grade ("Reprovado por Faltas").
