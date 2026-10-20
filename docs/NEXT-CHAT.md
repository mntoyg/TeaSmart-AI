# Handoff prompt for the next chat

Paste the block below into a new chat. It is rewritten at the end of each
session, by the session that is ending, so it is always current.

---

```
You are continuing TeaSmart AI at D:\code-project\TeaSmart AI.

FIRST, BEFORE ANY WORK, report two numbers to me:
1. Context window: how much of this chat's context is used and how much is left.
2. Weekly usage: the current figure, and how much of today's 14% allowance is
   left. The ceiling is 14 percentage points of WEEKLY capacity per calendar
   day (Asia/Bangkok), not 14% of the remaining balance.
   - Baseline for 2026-10-20 was 28%. If today is still 2026-10-20, today's
     allowance left = 14 - (current - 28).
   - If today is a later date, record a fresh baseline as the first reading of
     the day and say so.
   Use the get_usage tool. If it is unavailable, say so and use a conservative
   bound rather than inventing a number.

THEN: read AGENTS.md and docs/STATE.md. Nothing else until you know what you
are doing. docs/DESIGN.md is the binding contract, docs/EVIDENCE.md has every
measured number with the command that produced it, docs/DEMO.md is the runbook.

WHEN THIS CHAT REACHES 70% CONTEXT:
Finish the task in progress and stop taking new ones. Then rewrite
docs/NEXT-CHAT.md with the current state, commit and push it, and give me the
new prompt to paste into the next chat. Keep doing this, chat after chat, until
the work is done. Do not wait for me to ask.

WHERE THINGS STAND (2026-10-20)
Demo is 2026-10-22. Everything is merged to main; there are no open PRs. The
API contract in DESIGN.md section 8 is fully implemented and every endpoint has
been verified live. 102 backend tests, 120 ml tests, 58 frontend tests, CI green
on four jobs.

THE ONE THING LEFT, AND I CANNOT DO IT
A run on a real phone, following "Testing on a real phone" in docs/DEMO.md.
It needs a secure context first: measured at http://<lan-ip>:5173 a browser has
isSecureContext false, and serviceWorker and mediaDevices are ABSENT - so no
camera, no offline, no install. Either add the origin to Chrome's
chrome://flags/#unsafely-treat-insecure-origin-as-secure on the phone, or use a
tunnel (which sends every photograph through a third party and is my decision,
not yours to assume).

Start the servers with:
  cd backend && .venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --port 8000
  cd frontend && npm run dev -- --host        # --host or the phone cannot reach it
Machine LAN address was 192.168.0.32. If the phone cannot load the page while
the machine can, it is almost always Windows Firewall on inbound 5173.

Expect me to report what happens on the phone. Fix what it surfaces.

STILL OPEN, IN PRIORITY ORDER
- P2: frontend/src/lib/api.ts hard-codes the class list, duplicating what
  GET /api/v1/config serves. Agrees today; a second copy is the problem.
- P2: parseKnowledge requires exactly 6 KB records, so a seventh disease breaks
  the client.
- P2: TEASMART_CORS_ORIGINS needs setting if the built PWA is served from an
  origin other than localhost:5173. The dev proxy hides this.
- P3: fp16 ONNX would cut the model from 16.8 MB to about 8.4 MB and is
  untested. The precache is 30.7 MB today.
- P3: two Kaggle sources and one gated HuggingFace source are disabled for want
  of credentials.
- P3: 32 photographs labelled differently by two sources are dropped rather
  than adjudicated.

THINGS THAT ARE TRUE AND EASY TO GET WRONG
- No sensitivity figure exists for burn detection and none may be quoted,
  including on stage. Specificity is 97.18%; sensitivity is unmeasurable
  without real burn photographs. EVIDENCE.md section 5.5.
- A high specificity can mean the analyser is not looking. The first run
  reported 99.22% while finding no lesion on 59% of diseased leaves.
- 0.987 test accuracy is an upper bound on field accuracy, not an estimate:
  the split is not grouped by photography session.
- No photograph in the corpus comes from Singha Park.
- Stage 1 thresholds and min_confidence are measured, not guessed. Re-measure
  rather than nudging them.
- A quoted bash heredoc eats \\n and apostrophes in Python source. Use the Write
  tool for scripts and commit messages.
- Never grep from the repository root: two .venv trees and data/ will hit the
  timeout.
- Run ./scripts/test.sh before pushing. CI caught a break I introduced by
  running only one suite after changing a fixture both suites read.

HOW I WANT YOU TO WORK
Reply in Thai; code, comments, commits and docs in English. Tests first, and
watch them fail. Never claim something works without pasting the command
output. Commit and push after every completed step, one branch per slice off
main, and open a PR rather than pushing to main. Update docs/STATE.md in the
same push as the work it describes.
```

---

## For whoever rewrites this file

Keep it the length it is. It exists so the next chat can start working inside
two tool calls, not so it can reconstruct the whole history: that is what
`docs/STATE.md`, `docs/EVIDENCE.md` and the git log are for.

Rewrite the dated sections - the state, the baseline, what is open - and leave
the standing instructions alone unless they turn out to be wrong.
