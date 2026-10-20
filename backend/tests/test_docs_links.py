"""Every relative link in the documentation must point at something that exists.

A judge or a new team member reading this repository follows links. One that
404s costs them the thread, and it is the cheapest possible defect to prevent:
the set of tracked files is knowable, so a link into it can be checked.

Only relative links are checked. An external URL needs the network and would
make the suite flaky, so it is out of scope here on purpose.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# [text](target) - the target is what gets checked.
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)")

# <img src="target"> - GitHub renders raw HTML in Markdown, and the README uses
# it to size the QR code. A broken src here shows a missing-image icon, which
# the link syntax above would never catch.
IMG_SRC = re.compile(r"<img\b[^>]*?\bsrc=[\"']([^\"']+)[\"']", re.IGNORECASE)

EXTERNAL = ("http://", "https://", "mailto:", "tel:", "data:")


def tracked_markdown() -> list[Path]:
    done = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [REPO_ROOT / line for line in done.stdout.split()]


def relative_links(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    out = []
    for target in LINK.findall(text) + IMG_SRC.findall(text):
        # Drop a fragment: README.md#section addresses a heading in README.md.
        bare = target.split("#", 1)[0].strip()
        if not bare or bare.startswith(EXTERNAL):
            continue
        out.append(bare)
    return out


def test_there_are_markdown_files_to_check() -> None:
    """Guards the lister: a change to it must fail here, not silently pass."""
    files = tracked_markdown()
    assert len(files) >= 5, files
    assert any(f.name == "README.md" for f in files), files


@pytest.mark.parametrize(
    "doc", tracked_markdown(), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_every_relative_link_resolves(doc: Path) -> None:
    broken = [
        target for target in relative_links(doc) if not (doc.parent / target).exists()
    ]
    assert not broken, (
        f"{doc.relative_to(REPO_ROOT)} links to files that do not exist: "
        f"{broken}. Point the link at the file that replaced it, or drop it."
    )
