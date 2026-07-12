#!/usr/bin/env bash
# Usage: pixi run check-python   (or: bash scripts/check.sh)
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Python syntax ==="
changed_py=$(git diff --name-only | grep '\.py$' || true)
if [ -z "$changed_py" ]; then
    changed_py=$(git diff --cached --name-only | grep '\.py$' || true)
fi
if [ -n "$changed_py" ]; then
    echo "$changed_py" | while read -r f; do
        python -m py_compile "$f" && echo "  OK: $f" || echo "  FAIL: $f"
    done
else
    echo "  no Python changes"
fi

echo "=== Frontend build ==="
cd frontend && pnpm exec vite build 2>&1 | tail -1
echo "  OK"
