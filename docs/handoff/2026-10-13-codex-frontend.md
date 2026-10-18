# Handoff to Codex — frontend slices D6 and D7

You are picking up the frontend of TeaSmart AI while Claude Code builds the
model and the API in parallel. Read this file, then `AGENTS.md`, then
`docs/STATE.md`. Nothing else, to begin with.

## Your ceiling

**14% of each AI's own weekly capacity per day**, updated 2026-10-19; `AGENTS.md`
defines the shared rule for every AI. Hard limit. Estimate the slice before the
first file read; if it does not fit in what is left today, build the part that
does and write the rest into `docs/STATE.md`. Stop at a committed, pushed
boundary — never with work only on your machine.

## What exists already

- `backend/` serves `GET /health` and `GET /api/v1/kb`, 40 tests green.
  `GET /api/v1/kb` returns the six knowledge-base records as JSON.
- `ml/` prepares the training corpus: 8,316 images, five classes, 70/15/15.
- `POST /api/v1/scan` **does not exist yet.** Claude Code builds it on D5. Its
  response shape is fixed in the spec, section 8, and is the contract between
  you and it.

## What you own

`frontend/` and, later, `mobile/`. Nobody else touches those directories. Do not
edit `backend/` or `ml/` — if you need something from them, say so in
`docs/STATE.md` and in your message to the user.

### D6 — the scan screen

React + Vite + TypeScript + Tailwind. Routes `/scan`, `/result/:id`,
`/history`, `/kb`.

- Camera capture via `getUserMedia`, plus a file picker fallback. A worker on a
  phone is the primary case; a judge on a laptop is the demo case.
- Post the image to `POST /api/v1/scan` and render the result.
- **Every string a user sees is in Thai.** Code, comments and commits in English.
- The result card shows, in this order: the disease name in Thai, the severity,
  whether the damage is disease or physical burn, and then the advice fields
  from the knowledge base. `physical_burn` must visibly **not** recommend
  spraying — that distinction is the whole point of the product.
- A rejected frame is not an error page. `422` comes back with `detail_th`
  telling the worker what to change ("ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น"); show
  that and let them retake immediately.
- Handle `413`, `415` and `400` the same way: they all carry `detail` and
  `detail_th`, and only `detail_th` is shown.

### D7 — offline

This is the feature the demo is judged on, because the network on a mountain
plot is not reliable.

- Service worker precaches the shell, the ONNX model and the knowledge base
  from `GET /api/v1/kb`.
- `onnxruntime-web` runs the int8 model in the browser. Claude Code exports it
  on D5 to `frontend/public/models/teasmart-v1-int8.onnx`. Until it lands,
  build against a stub with the same input and output shape: input
  `[1, 3, 224, 224]` float32 NCHW, output `[1, 5]` logits over
  `["grey_blight", "brown_blight", "algal_spot", "healthy", "other_disease"]`.
- Queue the image and its local result in IndexedDB, and replay it through
  `POST /api/v1/sync/batch` when connectivity returns, which fills in the
  lesion analysis and severity the browser cannot compute.
- **The result card must say which mode produced it.** A field worker must never
  be left thinking a classifier-only answer was a full analysis. Being honest
  about that is worth more than looking seamless.

## Do not hard-code a constant that the backend also has

`GET /api/v1/config` serves every number that exists on both sides: the
confidence floor, the class order, the ONNX preprocessing, and the quality-gate
thresholds your JavaScript copy of stage 1 needs. Fetch it once, cache it in the
service worker next to the knowledge base, and read from it.

`min_confidence` is 0.60 today and is explicitly provisional: D3 replaces it
with a value measured on the validation split. A copy of it in TypeScript would
go stale the moment that happens, and nothing in either codebase could see the
disagreement. The same is true of the quality thresholds, which are the one
piece of logic deliberately implemented twice.

## Before you write the API client

Read section 8 of `docs/superpowers/specs/2026-10-13-teasmart-ai-design.md` for
the exact response shape, and generate your TypeScript types from it rather than
hand-writing them from this summary. **Do not change the contract.** If it is
wrong, say so in `docs/STATE.md` and to the user, and wait.

## How to work here

- `npm` in `frontend/`. Vitest for tests, covering the offline queue and the
  ONNX pre- and post-processing.
- **Write the test first and watch it fail.** A test that passed the moment you
  wrote it proves nothing.
- Branch per slice off `main`: `feat/d6-scan-ui`, then `feat/d7-offline`. Never
  commit to `main`. Conventional commits, body explaining **why**.
- **Commit and push after every completed step**, not at the end of the session.
- Update `docs/STATE.md` when a slice is done, in the same push. It is how
  Claude Code learns what happened.
- Never commit secrets. `.env`, tokens and `private/` are gitignored and denied
  to tools.

## Two things that will cost you a round trip if nobody warns you

- `grep -rn` from the repository root walks two `.venv` trees and `data/` and
  hits the command timeout. Scope every search.
- The repository path contains a space: `D:\code-project\TeaSmart AI`. Quote it.

## When something is unclear

Ask the user one or two sharp questions in Thai. Do not guess: this app tells
tea farmers whether to spray fungicide, and a plausible-looking guess is worse
than a question.
