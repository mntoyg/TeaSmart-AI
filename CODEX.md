# CODEX.md

**Read [AGENTS.md](AGENTS.md).** It is the single source of truth for this
project: the rules, the architecture, the constraints, and the token discipline.
Then read [docs/STATE.md](docs/STATE.md) for where the work currently stands.

Codex reads `AGENTS.md` automatically; this file only adds what is specific to
working here as Codex.

## The three rules most easily forgotten

1. Reply in **Thai**. Code and commits in English.
2. **Commit and push after every completed step**, not at the end of the session.
3. Run tests through the package venv: `./.venv/Scripts/python.exe -m pytest -q`
   from `backend/` or from `ml/`. A bare `python` has none of the dependencies.

## Your daily usage ceiling: 13.5% of weekly capacity

This is a hard limit, not a target. Claude Code works to 15% per day in the same
repository, so the two ceilings together are what keeps the week solvent through
the 2026-10-22 deadline.

How to hold it:

- **Estimate before you start, not while you work.** Decide what the slice costs
  before the first file read. If it does not fit in what is left today, do the
  part that does and leave the rest in `docs/STATE.md`.
- **Orient from `docs/STATE.md`**, not from a tree walk, a `git log`, or reading
  the spec end to end. That file is written to answer where things stand in 60
  lines.
- **Read the one task you are on**, not the whole plan.
- **Stop at a committed boundary.** When the ceiling is close, finish the step in
  progress, commit, push, update `docs/STATE.md`, and report what is left. Never
  stop with work only on your machine, and never stop mid-file.
- Scope every search. `grep -rn` from the repository root walks two `.venv`
  trees and `data/` and will hit the command timeout.

## Division of labour

Claude Code and Codex both work in this repository, on separate branches, and
the daily usage budgets are separate too (Codex is held to a tighter share than
Claude). To avoid two agents rediscovering the same ground:

- **Check `docs/STATE.md` for the open branch before starting.** If a slice is
  already in flight, pick the next independent one rather than a second opinion
  on the same files.
- One branch per slice, never two agents on one branch.
- Whoever finishes a slice updates `docs/STATE.md` in the same push. That file
  is how the other agent learns what happened without reading a diff.
- Rulings and deviations go in `docs/superpowers/decisions/`, with the reason
  and what it costs if the call was wrong. The next agent needs the reason more
  than the decision.

## Where to be careful

- `backend/app/kb/diseases.json` is agronomy advice a farmer acts on. Records
  0-3 are supplied text; do not reword them, do not translate them, do not
  "improve" the phrasing.
- `backend/app/core/images.py` is the only door untrusted images come through,
  and every later stage relies on its guarantees. Any change needs a test for
  the specific input class you are worried about.
- `ml/teasmart_ml/datasets/dedup.py` decides what the model never sees. Its
  threshold and its exactness argument are documented in the module docstring
  and were reached after two wrong answers; read that before touching it.

## Environment notes

- Windows paths with spaces: quote them. The repository root is
  `D:\code-project\TeaSmart AI`.
- Two virtualenvs, `backend/.venv` and `ml/.venv`, with different dependency
  sets. Neither is on `PATH`.
- Both suites run with `filterwarnings = error`.
- Long operations (dataset preparation, training) take minutes; do not let them
  block an interactive turn.
