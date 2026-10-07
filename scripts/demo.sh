#!/usr/bin/env bash
# Offline toy end-to-end run through every stage using the conformance toy implementation.
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh
exec "$PY" scripts/demo.py
