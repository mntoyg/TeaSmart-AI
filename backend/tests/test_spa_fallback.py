"""A deployed static host must serve the app for paths only the router knows.

Routing is client-side: `frontend/src/App.tsx` declares /scan, /result/:id,
/history and /kb, and nothing but `/` and the built asset paths exist as files.
On a static host a request for /result/<id> - the link someone shares, or the
start_url the installed PWA fetches on a cold cache - therefore reaches the
host's own 404 page unless a catch-all rewrite sends it to index.html.

`frontend/public/_redirects` is that rewrite, and Vite copies it to the root of
`dist`. Cloudflare Pages and Netlify both read it. The failure it prevents is
invisible in development, because Vite's dev server has its own SPA fallback,
and it only appears once a judge taps a link.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REDIRECTS = REPO_ROOT / "frontend" / "public" / "_redirects"
APP_TSX = REPO_ROOT / "frontend" / "src" / "App.tsx"


@pytest.fixture(scope="module")
def rules() -> list[tuple[str, str, str]]:
    assert REDIRECTS.is_file(), (
        f"{REDIRECTS.relative_to(REPO_ROOT)} is missing. Without it every "
        "client-side route 404s on a static host."
    )
    out = []
    for line in REDIRECTS.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        assert len(parts) == 3, f"cannot read rule {line!r}: expected 3 fields"
        out.append((parts[0], parts[1], parts[2]))
    return out


def test_the_app_still_routes_client_side(rules) -> None:
    """Guards the premise: if routing ever moves server-side, this file is moot.

    It reads App.tsx rather than trusting the docstring above, so the day
    someone switches to file-based routes this test says so instead of silently
    protecting nothing.
    """
    assert "BrowserRouter" in (REPO_ROOT / "frontend" / "src" / "main.tsx").read_text(
        encoding="utf-8"
    ), "main.tsx no longer mounts BrowserRouter; re-check whether _redirects is needed"
    declared = re.findall(r'<Route\s+path="([^"]+)"', APP_TSX.read_text(encoding="utf-8"))
    assert declared, "App.tsx declares no routes; this test cannot check anything"
    assert any(path.startswith("/") for path in declared), declared


def test_a_catch_all_sends_every_unknown_path_to_the_app(rules) -> None:
    catch_all = [rule for rule in rules if rule[0] in {"/*", "/*/"}]
    assert catch_all, (
        f"no catch-all rule in {REDIRECTS.relative_to(REPO_ROOT)}; rules found: "
        f"{rules}. A shared /result/<id> link would reach the host's 404 page."
    )
    for source, destination, status in catch_all:
        assert destination == "/index.html", (
            f"{source} rewrites to {destination}; it has to be /index.html, "
            "which is the only document the router is mounted in."
        )
        assert status == "200", (
            f"{source} uses status {status}. A redirect changes the URL, and "
            "the path is exactly what the router reads, so it must be 200."
        )


def test_the_catch_all_is_last(rules) -> None:
    """Rules are evaluated in order, so a catch-all above a rule hides it."""
    sources = [rule[0] for rule in rules]
    if "/*" in sources:
        assert sources.index("/*") == len(sources) - 1, (
            f"the catch-all is not the last rule: {sources}. Everything after "
            "it is unreachable."
        )
