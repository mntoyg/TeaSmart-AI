# Project structure

Start with [STATE.md](STATE.md) for current delivery status. The tracked layout
is the same in a team clone and on GitHub:

```text
TeaSmart-AI/
  README.md                 Project entrypoint and quick start
  AGENTS.md                 Rules for every AI contributor
  CONTRIBUTING.md           Shared review and contribution rules
  frontend/                 React, TypeScript, Vite and offline PWA
    src/
      pages/                Capture/scan screen
      components/           Reusable result presentation
      lib/                  API, persistence, queue, inference and quality
      test/                 Shared test setup and fixtures
      App.tsx               Routes, history/KB views and app coordination
      main.tsx              App bootstrap
      styles.css            Shared styles
      sw.ts                 Service worker
    public/                 Icons; models/ receives the ignored ONNX asset
    scripts/                Generate/check types from the shared spec
    package.json            Frontend commands
    README.md               Detailed source map and PWA instructions
  backend/                  Python API and six-stage pipeline
    app/core/               Configuration and hardened image decoding
    app/services/           Pure pipeline stages
    app/api/v1/             Versioned endpoints
    app/kb/                 Curated Thai advice; preserve supplied text
    tests/                  Backend regression tests
  ml/                       Dataset pipeline; training/export still pending
    teasmart_ml/             Python package
    tests/                  Dataset pipeline tests
  docs/
    STATE.md                Current status and next work
    FRONTEND_TEAM.md        Team onboarding and task boundaries
    PROJECT_STRUCTURE.md    This map
    handoff/                Handoff briefs
    eval/                   Measured evidence
    superpowers/            Binding specs, execution plans and decisions
```

`mobile/` is planned for Capacitor and has not been implemented. Do not infer
completion from a folder mentioned in the design spec.

## Local-only folders

`node_modules/`, `dist/`, `.venv/`, caches and `data/` are generated or ignored.
`private/` is tool-denied and must never supply committed images or secrets.
`.superpowers/worktrees/` contains old independent Git checkouts. It is not the
frontend source location for the team; leave those checkouts intact.

Do not move `backend/`, `ml/`, dataset roots or model paths to tidy the tree:
their paths are part of the current tooling and the agreed API/model contract.
