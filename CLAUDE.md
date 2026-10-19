# CLAUDE.md

**Read [AGENTS.md](AGENTS.md).** It is the single source of truth for this
project: the rules, the architecture, the constraints, and the token discipline.
Then read [docs/STATE.md](docs/STATE.md) for where the work currently stands.

This file only adds what is specific to Claude Code.

## The three rules most easily forgotten

1. Reply in **Thai**. Code and commits in English.
2. **Commit and push after every completed step**, not at the end of the session.
3. Run tests through the package venv: `./.venv/Scripts/python.exe -m pytest -q`
   from `backend/` or from `ml/`. A bare `python` has none of the dependencies.

## Workflow

This project is built with the superpowers skills, in this order:

| situation | skill |
|---|---|
| a new slice or feature | `superpowers:brainstorming` → `writing-plans` → `executing-plans` |
| a bug or unexpected result | `superpowers:systematic-debugging` |
| about to claim something works | `superpowers:verification-before-completion` |
| a branch is finished | `superpowers:requesting-code-review`, then `finishing-a-development-branch` |

There is no separate plan file any more. When executing a slice, read its brief
rather than the whole plan, and keep the ledger line in the same tool call as
the commit — context does not survive compaction, the ledger does.

**At roughly 70% context**, finish the task in progress, then write the next
session a handoff prompt, update `docs/STATE.md`, push, and hand it over.
The hard daily usage ceiling in `AGENTS.md` takes precedence over this context
guideline: every AI must stop at a pushed boundary before using more than 14%
of its own weekly capacity in a Bangkok calendar day.

## Environment notes that cost a round trip each

- Bash heredocs in this environment break when the body contains an apostrophe.
  Use the Write tool, or write a patch script into the scratchpad and run it.
- `grep -rn` from the repository root walks both `.venv` trees and `data/` and
  hits the command timeout. Scope every search to `ml/teasmart_ml` or
  `backend/app`.
- The two test suites have separate virtualenvs. Run them as two commands.
- Mendeley refuses urllib3 and answers curl, so `ml` shells out to curl for
  those downloads. This is deliberate; see the ruling in
  `docs/DESIGN.md` section 13, next to the decisions already recorded there.
- Long runs (dataset preparation, training) belong in the background.

## What not to read

`data/`, both `.venv/` trees, and `*.onnx` are noise in your context and are
listed in `.claudeignore`. Credentials are denied outright in
`.claude/settings.json`. If a file there looks necessary, ask first.
