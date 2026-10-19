# Contributing to TeaSmart AI

Phase 1 MVP, hackathon demo on **2026-10-22**. One vertical slice lands per day.
Read `docs/STATE.md` to see where things stand, then `docs/DESIGN.md` before
touching code.

Frontend contributors: read [the team guide](docs/FRONTEND_TEAM.md) and
[the project map](docs/PROJECT_STRUCTURE.md). Work in root `frontend/` on the
integration branch until it is merged; do not develop inside historical hidden
worktrees. Every AI contributor follows the 14% daily ceiling in `AGENTS.md`.

| document | what it is |
|---|---|
| `docs/STATE.md` | where the work stands right now — update it when you finish a slice |
| `docs/DESIGN.md` | design, the API contract and the decisions behind them — the binding authority when anything disagrees |
| `docs/EVIDENCE.md` | the measured numbers, and the commands that produced them |
| `AGENTS.md` | the rules AI agents work under |

## Get set up

```bash
git clone https://github.com/mntoyg/TeaSmart-AI.git && cd TeaSmart-AI
./scripts/setup.sh --cpu     # Windows: ./scripts/setup.ps1 -Cpu
./scripts/test.sh            # Windows: ./scripts/test.ps1
```

Drop `--cpu` if you have an NVIDIA card and intend to train. Everything in the
test suites runs on the CPU, so the CPU wheel is enough to contribute.

`test.sh` should end with `All green.` It runs exactly what CI runs, in the same
order, so a green run locally is a green run on the pull request. At the time of
writing that is 46 backend tests, 120 ML tests and 47 frontend tests.

Python 3.12 and Node 22 are required. Nothing needs a `.env` to run; copy
`.env.example` to `backend/.env` only to override a default.

## Run the service

```bash
cd backend && .venv/bin/python -m uvicorn app.main:create_app --factory --reload
```

On Windows the interpreter is `.venv/Scripts/python.exe`. The virtualenvs are
never activated - naming the interpreter is one line longer and removes a whole
class of "wrong environment" mistakes.

```bash
curl http://127.0.0.1:8000/health && curl http://127.0.0.1:8000/api/v1/config
```

## The ML package

```bash
cd ml
.venv/bin/python -m teasmart_ml.cli --help
.venv/bin/python -m teasmart_ml.cli prepare     # rebuild the corpus
.venv/bin/python -m teasmart_ml.cli train       # ~35 min on a 4 GB card
.venv/bin/python -m teasmart_ml.cli evaluate --split test
.venv/bin/python -m teasmart_ml.cli export      # ONNX for the browser
.venv/bin/python -m teasmart_ml.cli fixtures    # browser parity fixtures
```

## House rules

**Tests first.** Write the failing test, watch it fail, then write the code. A
test that passed the moment you wrote it proves nothing; if you add a test that
cannot fail, change a constant to make it fail, confirm it does, and change it
back.

**The suite treats warnings as errors.** A green run is also a clean run. If a
third-party warning appears, add a targeted ignore in the `filterwarnings` list
in that package's `pyproject.toml` — message, category and module — never a
blanket one.

**Lint is part of the suite, not a separate chore.** `ruff check` runs before
the tests in `scripts/test.*` and in CI. It is currently clean; keep it that
way rather than letting a backlog form.

**Thresholds live in config, not at call sites.** Everything tunable is a field
on `Settings` in `backend/app/core/config.py`, and `tests/test_config.py` pins
the values the spec fixes. Read them from `get_settings()` in tests rather than
hard-coding the numbers again.

**The knowledge base is data.** `backend/app/kb/diseases.json` holds the Thai
advice a farmer acts on. Records 0-3 are supplied text and are not to be
reworded. Records are keyed by the `canonical` snake_case class the classifier
emits, not by the English display name.

**Thai is for people, English is for code.** User-facing strings and knowledge
base content in Thai; code, comments, docstrings, commit messages and these docs
in English.

**Every pipeline stage is a pure function.** One module per stage under
`backend/app/services/`, no stage reaching into another's internals. If a stage
needs a value, it takes it as an argument.

**Uploads are hostile until proven otherwise.** `backend/app/core/images.py` is
the only door images from outside come through, and every later stage trusts its
output. Changes there need a test for the input class you are worried about.

## Branches and commits

Branch per slice, off `main`: `feat/d2-dataset-ingest`, `fix/...`, `docs/...`.
Never commit straight to `main`. Two agents work here in parallel and the split
is by directory — `docs/DESIGN.md` section 14 says who owns what. One branch per
slice; never two people on one branch.

Conventional-commit subjects (`feat(kb):`, `fix:`, `docs:`), imperative mood,
then a body explaining **why** — the diff already says what. Include the test
result when it is the point of the change.

Open a PR against `main` and have someone read it. The PR body says what landed,
which decisions are worth knowing about, and the verification output.

## Before you say it works

Run the suite and paste the real output. "Should work" is not evidence. If
something is incomplete or you skipped a step, say so in the PR.
