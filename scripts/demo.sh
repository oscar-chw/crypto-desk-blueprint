#!/usr/bin/env bash
# Offline toy end-to-end run through every stage using the conformance toy implementation.
set -euo pipefail
cd "$(dirname "$0")/.."
exec "${PY:-python}" scripts/demo.py
