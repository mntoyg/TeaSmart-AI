# TeaSmart AI

A smart-farming assistant for large-scale Oolong tea estates: photograph a tea
leaf and the system reports the disease and its severity, tells you whether the
damage is a biological disease or a physical burn, and returns actionable Thai
treatment advice from a curated expert knowledge base. It runs on-device so it
keeps working where the mountain network does not.

## Status

Phase 1 MVP, under active development for a 2026-10-22 hackathon demo.

- Design spec: `docs/superpowers/specs/2026-10-13-teasmart-ai-design.md`
- Current plan: `docs/superpowers/plans/2026-10-13-d1-foundation.md`

## Backend setup

```bash
cd backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt    # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # Linux / macOS
```

Copy `.env.example` to `backend/.env` if you need to override any default. No
secrets are required to run the service.

## Run the service

```bash
cd backend
.venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --reload
```

Then check it:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/kb
```

## Run the tests

```bash
cd backend
.venv/Scripts/python.exe -m pytest -v
```

The suite treats warnings as errors, so a green run is also a clean run.

## Layout

| path | holds |
|---|---|
| `backend/app/core/` | configuration and hardened image loading |
| `backend/app/services/` | one module per pipeline stage |
| `backend/app/kb/` | the Thai disease knowledge base (data, never code) |
| `ml/` | dataset ingestion, training, evaluation, ONNX export |
| `frontend/` | the PWA that runs the model on-device |
| `data/` | datasets and intermediates, never committed |
