"""Generate the QR code the README shows, from the URL the app is served at.

The point of a QR in the README is that someone in the room scans it and the
app opens on their own phone - no install, no certificate, no cable. That only
works if the URL is one a stranger can reach, so this refuses a localhost or
private-network address unless `--allow-local` says that is deliberate.

    python scripts/make_qr.py https://<deployed-host>/scan

After a deployment, re-run it with the public URL and commit the PNG; the
README does not need editing, because it points at a fixed path.

For testing on your own handset, where a LAN address is the right answer:

    python scripts/make_qr.py https://192.168.0.32:5173/scan \\
      --out docs/img/app-qr-local.png --allow-local
"""

from __future__ import annotations

import argparse
import ipaddress
from pathlib import Path
from urllib.parse import urlsplit

import segno

DEFAULT_OUT = Path("docs/img/app-qr.png")

# A host ending in one of these is resolved by the local machine or network and
# means nothing to someone else's phone.
LOCAL_SUFFIXES = (".local", ".localhost", ".internal", ".home", ".lan")
LOCAL_NAMES = ("localhost",)


def check_url(url: str) -> str:
    """The URL, or `ValueError` if a phone's camera could not open it."""
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError(
            f"{url!r} is not an http or https URL with a host. A QR code is "
            "scanned by a camera, which will only offer to open one of those."
        )
    return url


def is_publicly_reachable(url: str) -> bool:
    """Whether a stranger's phone, on its own network, could open this URL."""
    host = urlsplit(url).hostname or ""
    lowered = host.lower()
    if lowered in LOCAL_NAMES or lowered.endswith(LOCAL_SUFFIXES):
        return False
    try:
        address = ipaddress.ip_address(lowered)
    except ValueError:
        return True  # a registered domain name
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
    )


def write_qr(
    url: str, out: Path, *, allow_local: bool = False, scale: int = 8
) -> Path:
    check_url(url)
    if not allow_local and not is_publicly_reachable(url):
        raise ValueError(
            f"{url!r} is a local or private address. A QR code of it works on "
            "your own phone and fails for everyone else, which is worse than "
            "no QR code: they conclude the app is broken. Deploy first, or "
            "pass --allow-local if a local QR is what you want."
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    # Error correction M tolerates a QR printed on a slide and photographed
    # from a few metres away.
    segno.make(url, error="m").save(out, scale=scale, border=2)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the README QR code.")
    parser.add_argument("url", help="the URL the app is served at")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--scale", type=int, default=8)
    parser.add_argument(
        "--allow-local",
        action="store_true",
        help="write a QR of a localhost or private address anyway",
    )
    args = parser.parse_args(argv)

    out = write_qr(
        args.url, args.out, allow_local=args.allow_local, scale=args.scale
    )
    reach = "public" if is_publicly_reachable(args.url) else "LOCAL ONLY"
    print(f"wrote {out} ({out.stat().st_size} bytes) for {args.url}  [{reach}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
