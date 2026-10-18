# Contributing to TeaSmart AI

Phase 1 MVP, hackathon demo on **2026-10-22**. One vertical slice lands per day;
read the spec before touching code.

Frontend contributors: read [the team guide](docs/FRONTEND_TEAM.md) and
[the project map](docs/PROJECT_STRUCTURE.md). Work in root `frontend/` on the
integration branch until it is merged; do not develop inside historical hidden
worktrees. Every AI contributor follows the 14% daily ceiling in `AGENTS.md`.

| document | what it is |
|---|---|
| `docs/superpowers/specs/2026-10-13-teasmart-ai-design.md` | the design spec — the binding authority when anything disagrees |
| `docs/superpowers/plans/` | the day's implementation plan, task by task |
| `docs/superpowers/decisions/` | rulings taken during execution, and the deferred items |
| `docs/STATE.md` | where the work stands right now — update it when you finish a slice |
| `AGENTS.md` | the rules AI agents work under; `CLAUDE.md` and `CODEX.md` point there |

## Get set up

```bash
git clone https://github.com/mntoyg/TeaSmart-AI.git && cd TeaSmart-AI/backend && python -m venv .venv && .venv/Scripts/python.exe -m pip install -r requirements.txt && .venv/Scripts/python.exe -m pytest -q
```

That last step should print `40 passed`. On Linux or macOS swap
`.venv/Scripts/python.exe` for `.venv/bin/python` throughout.

Python 3.12 is required. Nothing needs a `.env` to run; copy `.env.example` to
`backend/.env` only if you want to override a default.

## Run the service

```bash
cd backend && .venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --reload
```

```bash
curl http://127.0.0.1:8000/health && curl http://127.0.0.1:8000/api/v1/kb
```

## Run the tests

```bash
cd backend && .venv/Scripts/python.exe -m pytest -q
```

Always run them from `backend/`, and always through the venv interpreter — the
system Python has none of the dependencies.

## House rules

**Tests first.** Write the failing test, watch it fail, then write the code. A
test that passed the moment you wrote it proves nothing; if you add a test that
cannot fail, change a constant to make it fail, confirm it does, and change it
back.

**The suite treats warnings as errors.** A green run is also a clean run. If a
third-party warning appears, add a targeted ignore in `backend/pytest.ini` —
message, category and module — never a blanket one.

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
Never commit straight to `main`.

Conventional-commit subjects (`feat(kb):`, `fix:`, `docs:`), imperative mood,
then a body explaining **why** — the diff already says what. Include the test
result when it is the point of the change.

Open a PR against `main` and have someone read it. The PR body says what landed,
which decisions are worth knowing about, and the verification output.

## Before you say it works

Run the suite and paste the real output. "Should work" is not evidence. If
something is incomplete or you skipped a step, say so in the PR.
