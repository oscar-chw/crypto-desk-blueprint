#!/usr/bin/env bash
# Exit 0 only if ruff (E9,F) is clean AND pytest passes AND pytest collected at least one test.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PY:-python}"
"$PY" -m ruff check --select E9,F pipeline conformance tests scripts
out="$("$PY" -m pytest -q 2>&1)" || { echo "$out"; echo "check: pytest failed"; exit 1; }
echo "$out" | tail -3
n="$(echo "$out" | grep -Eo '[0-9]+ passed' | head -1 | grep -Eo '[0-9]+' || echo 0)"
[ "${n:-0}" -ge 1 ] || { echo "check: pytest collected 0 tests"; exit 1; }
echo "check: ok ($n tests)"
