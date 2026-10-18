# Frontend team onboarding

## Get the shared checkout

Until the integration PR is merged, a new contributor starts with:

```powershell
git clone --branch codex/team-onboarding https://github.com/mntoyg/TeaSmart-AI.git
cd TeaSmart-AI
git switch -c feat/your-frontend-task
cd frontend
npm ci
npm run dev
```

After the integration PR is merged, branch from updated `main` instead. Do not
share a working branch or copy files from `.superpowers/worktrees/d6` or `d7`.
Use Git commits/PRs to share changes. Never discard an existing checkout's local
changes to follow these instructions.

Open `http://localhost:5173/scan`. Node 22.12+ is required. Vite forwards `/api`
to the local Python service at `http://127.0.0.1:8000`. Backend setup is in the
root README; the real scan/sync endpoints are still pending D5.

## Pick a task without colliding

| task | primary files | coordinate before editing |
|---|---|---|
| scan/camera UX | `frontend/src/pages/ScanPage.tsx` | capture IDs, queue behavior |
| result cards | `frontend/src/components/ResultCard.tsx` | analysis mode and supplied advice |
| styles/accessibility | `frontend/src/styles.css`, relevant components | shared navigation/layout |
| history/knowledge views | `frontend/src/App.tsx` | routing and app coordinator changes |
| offline/sync | `frontend/src/lib/`, `frontend/src/sw.ts` | API/model contract and parity |

Call out shared files in your PR description and keep branches short. Tests live
beside the code they cover; shared fixtures are in `frontend/src/test/`.
The [frontend source map](../frontend/README.md#source-map) explains each module.

## Before opening a PR

```powershell
cd frontend
npm run test:contract
npm test
npm run build
```

Write regression tests before changing behavior and observe the failure. UI
text is Thai; code, comments, commits and documentation are English. Update
`docs/STATE.md` with completed work and any remaining validation, commit and push
each completed step, and let a human merge. Every AI follows the 14% hard daily
ceiling in root `AGENTS.md`.

## Integration boundaries

The contract in [spec section 8](superpowers/specs/2026-10-13-teasmart-ai-design.md)
is shared with Claude Code's backend/ML work. Do not change it alone. API types
are generated; inference thresholds and preprocessing come from `/api/v1/config`.
Advice comes from the curated KB and must not be rewritten casually.

D6 UI and D7 infrastructure exist, but D7 is not certified complete. The real
model, 50-image Python/browser parity, live endpoint/reconnect checks and demo
phone validation are still required. A classifier-only result must never claim
that burn analysis or severity was computed. The app ships no fake model.
