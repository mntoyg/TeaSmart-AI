#!/usr/bin/env bash
# Everything CI runs, in the same order, so a green run here means a green run
# there. Linux, macOS, CI.
#
#   ./scripts/test.sh          everything present in this checkout
#   ./scripts/test.sh --quick  skip the frontend build, which is the slow part
#
# Runs every step even after one fails, then reports all of them: finding out
# about the second failure on the next run wastes a round trip.

set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
quick="${1:-}"
failures=()

venv_python() {
  local dir="$1"
  [[ -x "$dir/.venv/bin/python" ]] && echo "$dir/.venv/bin/python" && return
  echo "$dir/.venv/Scripts/python.exe"
}

backend="$(venv_python "$root/backend")"
ml="$(venv_python "$root/ml")"

if [[ ! -x "$backend" || ! -x "$ml" ]]; then
  echo "Virtualenvs are missing. Run ./scripts/setup.sh first." >&2
  exit 1
fi

step() {
  local name="$1"; shift
  echo
  echo "--- $name"
  if ! "$@"; then
    failures+=("$name")
    echo "FAILED: $name"
  fi
}

# Lint before tests: an import-order complaint should not wait behind a
# four-minute suite.
step 'lint backend' bash -c "cd '$root/backend' && '$ml' -m ruff check app tests"
step 'lint ml' bash -c "cd '$root/ml' && '$ml' -m ruff check teasmart_ml tests"
step 'test backend' bash -c "cd '$root/backend' && '$backend' -m pytest -q"
step 'test ml' bash -c "cd '$root/ml' && '$ml' -m pytest -q"

if [[ -f "$root/frontend/package.json" ]]; then
  step 'test frontend' bash -c "cd '$root/frontend' && npm test --silent"
  if [[ "$quick" != "--quick" ]]; then
    step 'build frontend' bash -c "cd '$root/frontend' && npm run build"
  fi
fi

echo
if (( ${#failures[@]} > 0 )); then
  printf 'FAILED: %s\n' "$(IFS=', '; echo "${failures[*]}")"
  exit 1
fi
echo 'All green.'
