# Sourced by check.sh and demo.sh. Interpreter: $PYTHON if set, else $PORTFOLIO_VENV/bin/python, else
# ./.venv/bin/python, else python3 on PATH (as in CI). A missing interpreter fails loudly, never as a pass.
if [ -n "${PYTHON:-}" ]; then PY="$PYTHON"
elif [ -n "${PORTFOLIO_VENV:-}" ]; then PY="$PORTFOLIO_VENV/bin/python"
elif [ -x .venv/bin/python ]; then PY=.venv/bin/python
else PY="$(command -v python3 || command -v python || true)"
fi
if [ -z "$PY" ] || ! "$PY" -m ruff --version >/dev/null 2>&1; then
  echo "error: no Python with the dev dependencies: pip install -e '.[dev]'" >&2
  exit 3
fi
export PYTHONDONTWRITEBYTECODE=1
