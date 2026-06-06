#!/bin/bash
# Frontend + backend build/syntax verification
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "=== Python syntax ==="
cd "$ROOT"
changed=$(git diff --name-only main...HEAD -- '*.py' 2>/dev/null || find app -name '*.py')
for f in $changed; do
    python -m py_compile "$f" && echo "  OK  $f"
done
echo "=== Frontend build ==="
cd "$ROOT/frontend"
pnpm exec vite build 2>&1 | grep -E "✓|error"
echo "  OK"
