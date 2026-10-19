#!/usr/bin/env bash
# One command to get a working checkout. Linux, macOS, CI.
#
#   ./scripts/setup.sh         GPU build of torch (needs an NVIDIA card)
#   ./scripts/setup.sh --cpu   CPU build, which is all the tests need
#
# Two virtualenvs on purpose: the API has no reason to carry torch, and the ML
# package has no reason to carry FastAPI. They are never activated - every
# command goes through the interpreter path explicitly, so there is no
# "which venv am I in" failure mode.

set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
torch_index="https://download.pytorch.org/whl/cu124"
[[ "${1:-}" == "--cpu" ]] && torch_index="https://download.pytorch.org/whl/cpu"

# Windows virtualenvs put the interpreter somewhere else. Git Bash on Windows
# hits this, so it is worth the two lines.
venv_python() {
  local dir="$1"
  [[ -x "$dir/.venv/bin/python" ]] && echo "$dir/.venv/bin/python" && return
  echo "$dir/.venv/Scripts/python.exe"
}

setup_package() {
  local package="$1"; shift
  local dir="$root/$package"
  local python
  python="$(venv_python "$dir")"

  if [[ ! -x "$python" ]]; then
    echo "creating $package/.venv"
    python3 -m venv "$dir/.venv"
    python="$(venv_python "$dir")"
  fi
  "$python" -m pip install --quiet --upgrade pip
  "$python" -m pip install --quiet -r "$dir/requirements.txt" "$@"
  echo "$package ready"
}

setup_package backend
setup_package ml --extra-index-url "$torch_index"

if [[ -f "$root/frontend/package.json" ]]; then
  cd "$root/frontend"
  if [[ -f package-lock.json ]]; then npm ci; else npm install; fi
  echo "frontend ready"
else
  echo "frontend not in this checkout; skipping"
fi

echo
echo "Done. Next: ./scripts/test.sh"
