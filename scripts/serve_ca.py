"""Hand the mkcert root certificate to a handset, and nothing else.

A handset trusts the dev server's TLS only once it trusts the mkcert root that
signed it. Getting that one public file onto a phone is the whole job: iOS in
particular installs a certificate from Safari only when the server says what it
is, so the content type below matters.

The file that sits next to it in `CAROOT` is `rootCA-key.pem` - the key that can
sign for any name on this machine. Handing that out over the LAN would be the
worst thing in this repository, so the handler does not consult the request path
at all. There is no path that reaches the key because the path is not an input.
`backend/tests/test_serve_ca.py` pins that property.

Run it, then open the printed URL on the handset:

    python scripts/serve_ca.py

Stop it as soon as the certificate is installed. It serves plain HTTP on
purpose: this is how trust is bootstrapped, so there is nothing to serve it
over yet. Only the public certificate crosses the wire.
"""

from __future__ import annotations

import argparse
import shutil
import socket
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CERT_NAME = "rootCA.pem"
KEY_NAME = "rootCA-key.pem"

# Safari offers to install a certificate only for this type; served as
# text/plain or application/octet-stream it lands in Files and the reader is
# left wondering what to do with it.
CONTENT_TYPE = "application/x-x509-ca-cert"

DEFAULT_PORT = 8081

# Resolved at run time to this machine's address on the network the default
# route uses. Listening on that one interface is enough for the handset, and
# avoids offering the certificate on every other adapter at once - VPN,
# VirtualBox, Docker - which binding to 0.0.0.0 would do. Pass --bind 0.0.0.0
# deliberately if that is really what is wanted.
DEFAULT_BIND = "lan"


def read_root_certificate(caroot: Path) -> bytes:
    """The bytes of the public root certificate in `caroot`.

    Raises `FileNotFoundError` if it is absent and `ValueError` if the file
    holds a private key, which would mean a `CAROOT` someone has rearranged by
    hand and must not be served.
    """
    path = caroot / CERT_NAME
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} does not exist. Generate a certificate with mkcert first, "
            "or pass --caroot."
        )
    body = path.read_bytes()
    if b"PRIVATE KEY" in body:
        raise ValueError(
            f"{path} contains a private key. Refusing to serve it. Only the "
            f"public {CERT_NAME} may leave this machine."
        )
    return body


def response_body(requested_path: str, certificate: bytes) -> bytes:
    """The response for any request.

    `requested_path` is accepted so that the signature documents the decision,
    and is deliberately unused: every request gets the certificate, so no
    crafted path - traversal, encoded, absolute - can select another file.
    """
    del requested_path
    return certificate


class _Handler(BaseHTTPRequestHandler):
    certificate: bytes = b""

    server_version = "TeaSmartCA/1"
    sys_version = ""

    def _send(self, *, body: bool) -> None:
        payload = response_body(self.path, self.certificate)
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPE)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header(
            "Content-Disposition", f'attachment; filename="{CERT_NAME}"'
        )
        self.end_headers()
        if body:
            self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 - the base class names it
        self._send(body=True)

    def do_HEAD(self) -> None:  # noqa: N802 - the base class names it
        self._send(body=False)

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write(f"  {self.address_string()} {fmt % args}\n")


def mkcert_caroot() -> Path | None:
    """Ask mkcert where its CA lives, or None if mkcert cannot be found.

    The name is resolved to a full path first. Running `mkcert` by bare name
    runs whatever the user's PATH points at first, and PATH is per-user and
    writable; resolving makes what runs explicit, and separates "not installed"
    from "ran something else".
    """
    executable = shutil.which("mkcert")
    if executable is None:
        return None
    try:
        done = subprocess.run(
            [executable, "-CAROOT"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    out = done.stdout.strip()
    return Path(out) if out else None


def lan_address() -> str:
    """This machine's address on the network the default route uses."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(("192.0.2.1", 1))  # reserved, no traffic is sent
            return str(probe.getsockname()[0])
        except OSError:
            return "127.0.0.1"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--caroot",
        type=Path,
        default=None,
        help="mkcert CAROOT; asks mkcert itself when omitted",
    )
    parser.add_argument(
        "--bind",
        default=DEFAULT_BIND,
        help="interface to listen on; the default is this machine's LAN "
        "address, which is the one the handset uses",
    )
    args = parser.parse_args(argv)
    bind = lan_address() if args.bind == DEFAULT_BIND else args.bind

    caroot = args.caroot or mkcert_caroot()
    if caroot is None:
        parser.error("mkcert is not on PATH; pass --caroot explicitly")

    certificate = read_root_certificate(caroot)
    _Handler.certificate = certificate

    print(f"serving {caroot / CERT_NAME} ({len(certificate)} bytes)")
    print(f"open this on the handset:  http://{lan_address()}:{args.port}/")
    print("every request returns the certificate; stop this once it is installed")

    with ThreadingHTTPServer((bind, args.port), _Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
