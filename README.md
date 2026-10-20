# TeaSmart AI

A smart-farming assistant for large-scale Oolong tea estates. Photograph a tea
leaf and the system reports the disease and its severity, says whether the
damage is a biological disease or a physical burn, and returns actionable Thai
treatment advice from a curated knowledge base. It runs the model on-device, so
it keeps working where the mountain network does not.

Phase 1 MVP, under active development for a 2026-10-22 hackathon demo.

## Quick start

```bash
./scripts/setup.sh --cpu     # Linux, macOS; drop --cpu if you have an NVIDIA card
./scripts/test.sh
```

```powershell
./scripts/setup.ps1 -Cpu     # Windows; drop -Cpu if you have an NVIDIA card
./scripts/test.ps1
```

Python 3.12 and Node 22. Nothing needs a `.env` to run; copy `.env.example` to
`backend/.env` only to override a default. No secrets are required.

Run the frontend against it:

```bash
cd frontend && npm run dev     # http://localhost:5173/scan
```

Vite forwards `/api` to `http://127.0.0.1:8000`, so both halves talk to each
other with no CORS setup in development.

Run the API:

```bash
cd backend && .venv/bin/python -m uvicorn app.main:create_app --factory --reload
curl http://127.0.0.1:8000/health
```

On Windows the interpreter is `.venv/Scripts/python.exe` instead.

## Layout

```
backend/        FastAPI service: image intake, pipeline stages, expert system
  app/api/v1/     HTTP surface, one module per endpoint group
  app/core/       config, and the single hardened door images come through
  app/services/   one module per pipeline stage, each a pure function
  app/kb/         the Thai disease knowledge base (data, never code)
  tests/
ml/             dataset pipeline, training, evaluation, ONNX export
  teasmart_ml/    importable package; `python -m teasmart_ml.cli --help`
  tests/
frontend/       the PWA that runs the model on-device
docs/           three files, no subfolders (see below)
scripts/        setup and test, for both shells
data/           datasets and intermediates, never committed
private/        local-only material, never committed
```

Each Python package owns its own virtualenv and its own `pyproject.toml`. They
are never activated: every command names the interpreter explicitly, so there is
no "which venv am I in" failure mode.

## Where to read

| file | what it is |
|---|---|
| [docs/STATE.md](docs/STATE.md) | where the work stands right now. **Start here.** |
| [docs/PHONE-TH.md](docs/PHONE-TH.md) | ภาษาไทย — opening the app on a real phone, with links to tap. Written to be read on the handset |
| [docs/DESIGN.md](docs/DESIGN.md) | design, the API contract, and the decisions behind both — the binding authority when anything disagrees |
| [docs/EVIDENCE.md](docs/EVIDENCE.md) | the measured numbers, and the commands that produced them |
| [docs/DEMO.md](docs/DEMO.md) | the demo runbook: running order, the measured outcome of every image, and the limits to state out loud |
| [CONTRIBUTING.md](CONTRIBUTING.md) | how to work here: house rules, branches, commits |
| [AGENTS.md](AGENTS.md) | the rules AI agents work under |

## Current numbers

Held-out test split, 1,245 images: **accuracy 0.9871, macro-F1 0.9873**. That is
an upper bound on field accuracy rather than an estimate, for reasons set out in
`docs/EVIDENCE.md` section 2.6. 166 Python tests and 47 frontend tests, run by
CI on every pull request.
