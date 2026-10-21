"""Freeze the two read-only endpoints into files a static host can serve.

The deployment chosen for the demo is the frontend alone, with no backend: a
judge opens one URL on their own phone, gets a real certificate and so a secure
context, and nothing they photograph leaves their device. Measured on the built
bundle with no server behind it, two requests 404:

    GET /api/v1/kb      -> 404
    GET /api/v1/config  -> 404

Both are fatal rather than cosmetic. Without `config` the on-device model
refuses to run at all ("ยังไม่มีการตั้งค่าออฟไลน์"), and without `kb` there is
no Thai advice - which is the product's entire output.

Hard-coding those values in the client is what `docs/DESIGN.md` section 8
forbids, and the reason an open P2 exists about `api.ts` duplicating the class
list. So this takes a snapshot of the running backend instead: the same bytes,
at the same paths, generated rather than retyped. The client needs no change,
and there is still one source of truth.

    cd backend && .venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --port 8000
    python scripts/snapshot_api.py
    cd frontend && npm run build

In development Vite proxies `/api` to the backend, which takes precedence over
these files, so they are only used by the built site.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from typing import Any

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "frontend" / "public" / "api" / "v1"

DEFAULT_BASE_URL = "http://127.0.0.1:8000"

# Endpoints that are read-only, identical for every caller, and small. POST
# /api/v1/scan is not here and cannot be: it runs the pipeline.
SNAPSHOTS = ("config", "kb")


def fetch(base_url: str, name: str, timeout: float = 15.0) -> Any:
    url = f"{base_url.rstrip('/')}/api/v1/{name}"
    # `--base-url` is an argument, and urlopen honours file: and other schemes.
    # Without this the script would happily read a local file and write its
    # contents into frontend/public/, where the next build publishes it. The
    # scheme is checked before anything is opened.
    scheme = urlsplit(url).scheme
    if scheme not in {"http", "https"}:
        raise ValueError(
            f"{url!r} is not an http or https URL (scheme {scheme!r}). "
            "This reads a running backend, nothing else."
        )
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
            if response.status != 200:
                raise RuntimeError(f"{url} answered {response.status}")
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError) as cause:
        raise RuntimeError(
            f"could not reach {url}: {cause}. Start the backend first - a "
            "snapshot taken from nothing would deploy a broken site."
        ) from cause


def check(config: Any, kb: Any) -> None:
    """Refuse a snapshot that would not work, before anything is written.

    The invariant worth stating is that the two files agree with each other:
    every class the classifier can emit must have advice to show for it.
    A snapshot where they disagree produces a result card with nothing in it,
    which on stage looks like the model failing.
    """
    if not isinstance(config, dict) or not isinstance(kb, list):
        raise ValueError(f"unexpected shapes: config {type(config)}, kb {type(kb)}")
    order = config.get("class_order")
    if not isinstance(order, list) or not order:
        raise ValueError(f"config has no usable class_order: {order!r}")
    if not isinstance(config.get("min_confidence"), (int, float)):
        raise ValueError("config has no numeric min_confidence")
    canonicals = {record.get("canonical") for record in kb if isinstance(record, dict)}
    missing = [name for name in order if name not in canonicals]
    if missing:
        raise ValueError(
            f"the knowledge base has no record for {missing}, which the "
            "classifier can emit. The result card would be empty."
        )


def write(name: str, payload: Any, out_dir: Path = OUT_DIR) -> Path:
    """Write the payload at the path the client asks for, extension and all.

    The file is named exactly `config` or `kb` because that is what the client
    requests. `Response.json()` parses the body whatever content type the host
    serves it with, so the missing extension does not matter to the app.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)

    payloads = {name: fetch(args.base_url, name) for name in SNAPSHOTS}
    check(payloads["config"], payloads["kb"])
    for name, payload in payloads.items():
        path = write(name, payload, args.out_dir)
        print(f"wrote {path.relative_to(REPO)} ({path.stat().st_size} bytes)")
    print("now run: cd frontend && npm run build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
