"""Nothing may reach a deployed bundle that this repository refused to commit.

Vite copies every file under `frontend/public/` into `dist` verbatim, and `dist`
is what gets uploaded to a public URL. Git tracking is the only review gate
those files pass through, so an untracked file there is one nobody agreed to
publish - and the two found on 2026-10-21, hours before a deployment, show what
that costs:

- `models/teasmart-v1-int8.onnx`, 4.7 MB. `docs/STATE.md` says it fails the
  parity bound (top-1 agreed on all 50 images but one probability moved by 0.248
  against a bound of 0.05) and to delete it if it is on your disk. It was being
  precached: removing it took the service worker from 13 entries to 12 and the
  offline download from 34.5 MB back to the 30.7 MB `docs/DEMO.md` quotes. Every
  judge's phone would have downloaded a model we had rejected.
- `parity/` - 50 photographs from the Kaggle, Mendeley and AGML corpora plus the
  answer sheet, 3.7 MB. `.gitignore` excludes them in as many words for
  "the same redistribution reasoning as demo/". Deploying would have published
  third-party dataset images on the open web.

Both are gitignored, so a fresh checkout is clean and only the machine that
generated them is affected. That is exactly the difference nobody notices until
it is live.

The invariant is the publishing boundary itself, not a list of filenames: if it
is under `public/` and git does not track it, it must not be there when the
bundle is built.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_DIR = REPO_ROOT / "frontend" / "public"
CONFIG_SNAPSHOT = PUBLIC_DIR / "api" / "v1" / "config"


@pytest.fixture(scope="module")
def contract_model() -> str:
    config = json.loads(CONFIG_SNAPSHOT.read_text(encoding="utf-8"))
    name = config.get("onnx", {}).get("file")
    assert isinstance(name, str) and name.endswith(".onnx"), (
        f"the config snapshot names no ONNX file to load: {name!r}. "
        "Regenerate it with: python scripts/snapshot_api.py"
    )
    return name


@pytest.fixture(scope="module")
def untracked() -> list[str]:
    """Files under frontend/public/ that git does not track.

    Deliberately without `--exclude-standard`: that flag honours .gitignore and
    so hides exactly the files this test exists to find. Both offenders were
    gitignored, which is why they survived every earlier check - being ignored
    keeps a file out of review but does nothing to keep it out of the bundle.
    Written with the flag first, this test passed against a public/ holding 52
    untracked files, and proved nothing.
    """
    done = subprocess.run(
        ["git", "ls-files", "--others", "frontend/public"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted(line for line in done.stdout.splitlines() if line.strip())


def test_the_contracts_model_is_present(contract_model: str) -> None:
    """Guards the premise: without this file the browser cannot classify."""
    path = PUBLIC_DIR / "models" / contract_model
    assert path.is_file(), (
        f"{path.relative_to(REPO_ROOT)} is missing, and it is the graph "
        "GET /api/v1/config tells the browser to load. Rebuild it with: "
        "cd ml && .venv/Scripts/python.exe -m teasmart_ml.cli export"
    )


def test_the_contracts_model_is_tracked(contract_model: str) -> None:
    """It ships, so it has to be reviewed like anything else that ships."""
    relative = f"frontend/public/models/{contract_model}"
    done = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, (
        f"{relative} is not tracked by git, yet the browser loads it. "
        "It is covered by the *.onnx rule, so it needs git add -f."
    )


def test_nothing_untracked_waits_under_public(untracked: list[str]) -> None:
    assert not untracked, (
        "these files are not tracked by git but would be copied into dist and "
        f"served from the deployed site: {untracked}. Nobody reviewed them. "
        "Move them out of frontend/public/ before building - parity assets are "
        "staged there for development by scripts/prepare_parity.py and are "
        "rebuilt in seconds, and a rejected model should not be there at all."
    )


def test_no_second_model_can_reach_the_bundle(contract_model: str) -> None:
    """Narrower than the check above, and survives it being relaxed."""
    extra = sorted(
        path.name
        for path in (PUBLIC_DIR / "models").glob("*.onnx")
        if path.name != contract_model
    )
    assert not extra, (
        f"{extra} would be served alongside {contract_model}. docs/STATE.md "
        "says to delete a rejected graph rather than leave it here."
    )
