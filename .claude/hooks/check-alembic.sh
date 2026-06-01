#!/bin/sh
# pre-push check: verify alembic migration exists for any model changes
# Usage: add to git pre-push hook or run manually before push

set -e

echo "=== Alembic migration check ==="

# Check if any model files changed vs main
CHANGED=$(git diff --name-only main...HEAD -- app/models/ | grep '\.py$' || true)

if [ -z "$CHANGED" ]; then
    echo "No model changes, skipping."
    exit 0
fi

# Check if any migration files were added/modified
MIGRATIONS=$(git diff --name-only main...HEAD -- migrations/versions/ | grep '\.py$' || true)

if [ -z "$MIGRATIONS" ]; then
    echo "ERROR: Model files changed but no alembic migration found."
    echo "Changed models:"
    echo "$CHANGED"
    echo ""
    echo "Run: alembic revision --autogenerate -m 'description'"
    exit 1
fi

echo "Model changes:"
echo "$CHANGED"
echo ""
echo "Migration files:"
echo "$MIGRATIONS"
echo "OK"
