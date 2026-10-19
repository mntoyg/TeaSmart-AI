# TeaSmart AI — directives for AI agents

**Single source of truth.** `CLAUDE.md` and `CODEX.md` point here and add only
what is specific to their tool. If they disagree with this file, this file wins.

**Read `docs/STATE.md` first.** It is 60 lines and tells you where the project
is right now. Do not reconstruct that from git log or by reading the whole tree.

---

## 1. Non-negotiable rules

1. **Reply to the user in Thai.** Code, comments, docstrings, commit messages
   and documentation stay in English.
2. **Commit and push after every completed activity.** Not at the end of the
   session — after each self-contained step. The repository is the record; an
   uncommitted machine is a single point of failure nine days from a deadline.
   `git push` to `origin`, private repo `mntoyg/TeaSmart-AI`.
3. **Never commit secrets or private imagery.** `.env`, API tokens,
   `kaggle.json`, and anything under `private/` are gitignored and denied to
   tools. If you need a credential, ask; do not invent or echo one.
4. **Tests first, and watch them fail.** A test that passed the moment you
   wrote it proves nothing. If you add a test that cannot fail, mutate the thing
   it guards, confirm it goes red, and change it back.
5. **Never claim something works without pasting the command output.** "Should
   work" is not evidence. If a step was skipped or is incomplete, say so.
6. **Do not run destructive commands without asking.** `rm -rf`, `git reset
   --hard`, force-push, dropping a directory. The dataset pipeline has a marker
   guard for exactly this reason.
7. **OWASP mindset on every input from outside.** Uploads, downloaded archives,
   and API responses are hostile until proven otherwise.
8. **Stay inside your daily usage ceiling**, measured against weekly capacity:
   **Claude Code 15% per day, Codex 13.5% per day.** Re-estimate before starting
   each item rather than discovering the limit mid-slice. If a ceiling is close,
   stop at a committed boundary, update `docs/STATE.md`, push, and say what is
   left — never leave work uncommitted on a machine.

## 1a. Two agents, one repository

Claude Code and Codex both work here, in parallel, on separate slices. The split
is by directory so that neither waits on the other:

| agent | owns | meets the other at |
|---|---|---|
| Claude Code | `ml/`, `backend/` — model, pipeline stages, API | the API contract in spec section 8 |
| Codex | `frontend/` — PWA, camera, Thai result cards | the same contract |

Rules that keep this from going wrong:

- **One branch per slice; never two agents on one branch.**
- Check `docs/STATE.md` for what is already in flight before you start. If your
  slice is taken, take the next independent one.
- Whoever finishes a slice updates `docs/STATE.md` in the same push. That file
  is how the other agent learns what happened without reading a diff.
- **The API contract is a shared interface: do not change it unilaterally.** If
  it has to change, write the change into the spec, say so in `docs/STATE.md`,
  and flag it to the user in the same message.

## 2. What this project is

A smart-farming assistant for large-scale Oolong tea estates (reference site:
Singha Park, Chiang Rai). Photograph a tea leaf, get the disease and its
severity, an explicit judgement of **disease versus physical burn**, and Thai
treatment advice from a curated knowledge base. **Hackathon demo 2026-10-22.**

The judging moment: someone picks up a phone, photographs a leaf, and gets a
correct Thai answer in seconds **with the network off**.

### Constraints that shape every decision

| constraint | consequence |
|---|---|
| RTX 3050 Laptop, 4 GB VRAM | MobileNetV3-Large at 224px. No ViT, no large backbone. |
| Unstable mountain network | On-device ONNX is the primary path; the server is an enhancement. |
| Nine days, capped daily AI usage | One vertical slice per day, each independently testable and pushed. |
| **No labelled burn images exist anywhere** | Burn detection is rule-based CV, never a trained class. Its headline metric is specificity on confirmed-disease images, not burn accuracy. |

### The pipeline

```
image -> [1] quality gate -> [2] leaf segment -> [3] classifier
      -> [4] lesion analyser (burn vs disease) -> [5] severity -> [6] expert system
```

Stages 1 and 6 ship. Stages 2-5 are D4-D5. Each stage is a pure function in its
own module under `backend/app/services/`, with no stage reaching into another.

### Five trained classes

`grey_blight`, `brown_blight`, `algal_spot`, `healthy`, `other_disease`.
`physical_burn` is a verdict stage 4 reaches, not a class the model learns.

`other_disease` exists so the model can say "an abnormality outside the three
primary diseases, have an agronomist look" instead of confidently naming the
wrong one. Do not remove it.

## 3. Where things are

| path | holds |
|---|---|
| `docs/STATE.md` | **read first** — current state, next step |
| `docs/DESIGN.md` | design, the API contract, and the decisions behind both: **the binding authority** |
| `docs/EVIDENCE.md` | measured evidence: corpus and model, with the commands |
| `backend/app/core/` | config and the hardened image door |
| `backend/app/services/` | one module per pipeline stage |
| `backend/app/kb/diseases.json` | the Thai advice a farmer acts on |
| `ml/teasmart_ml/` | dataset ingest, dedup, manifest, training |
| `data/` | datasets and intermediates — gitignored, never committed |
| `private/` | real farm photos if we ever get them — gitignored and tool-denied |

## 4. Working here without burning tokens

This section exists because the usage budget is a hard constraint, not a
preference. Every item below cost real tokens to learn.

**Orient cheaply.** `docs/STATE.md`, then the current plan's task you are on.
Not the whole spec, not `git log`, not a tree walk.

**Two virtualenvs, and the system Python has neither.** Always:

```bash
cd backend && ./.venv/Scripts/python.exe -m pytest -q
cd ml && ./.venv/Scripts/python.exe -m pytest -q
```

A bare `python -m pytest` fails with a confusing import error and costs a round
trip. On Linux or macOS swap `Scripts/python.exe` for `bin/python`.

**Never `grep -rn` from the repository root.** It walks both `.venv` trees and
`data/` and will blow the command timeout. Scope it: `grep -rn pattern ml/teasmart_ml backend/app`.

**Bash heredocs break in this environment** when the body contains an
apostrophe. Repeatedly. Write code with the Write tool, or put a patch script in
a scratch directory and run it. Do not spend three attempts rediscovering this.

**Prefer one compound command over three round trips.** Each tool call re-reads
your whole context. Bookkeeping rides along with real work.

**Redirect long output to a file and read its tail.** A 70 KB test log in your
context is paid for on every subsequent turn.

**Background the long things.** Dataset preparation and training take minutes;
run them in the background and keep working.

## 5. House rules for the code

**Thresholds live in config, not at call sites.** Everything tunable is a field
on `Settings` in `backend/app/core/config.py`, and `tests/test_config.py` pins
the values the spec fixes. Read them from `get_settings()` in tests rather than
hard-coding the numbers again.

**The knowledge base is data.** `backend/app/kb/diseases.json` holds advice a
farmer acts on. Records 0-3 are supplied text and are not to be reworded.
Records are keyed by the `canonical` snake_case class the classifier emits.

**Warnings are errors.** Both suites run with `filterwarnings = error`, so a
green run is a clean run. A third-party warning gets a targeted ignore in that
package's `pytest.ini` — message, category and module — never a blanket one.

**Uploads are the only door.** `backend/app/core/images.py` guarantees a
C-contiguous uint8 RGB array, upright, metadata stripped. Every later stage
trusts that. Changes there need a test for the input class you are worried about.

**Measure, do not assume — then audit the measurement.** The hardest bug of D2
was a verification that only examined the cases the implementation had already
chosen, and so reported success while 3.24% of the evaluation set was leaking.
State an invariant in terms of the property, never in terms of your own
algorithm. `docs/DESIGN.md` section 13 has the detail.

## 6. Git

Branch per slice off `main`: `feat/d3-training`, `fix/...`, `docs/...`. Never
commit straight to `main`.

Conventional-commit subjects (`feat(ml):`, `fix:`, `docs:`), imperative mood,
then a body explaining **why** — the diff already says what. Include the test
result when it is the point of the change.

Commits are authored with the GitHub noreply address; do not change the git
identity. Open a PR against `main` and let a human merge it.

## 7. When context is missing

Stop and ask one or two sharp questions. Do not guess: a wrong assumption here
becomes agronomy advice someone sprays on a field. If you raise a concern and
the user reaffirms the request, that is their decision — say so once and
proceed with the full request.
