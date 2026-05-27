#!/usr/bin/env bash
# Check dev environment readiness — docker services + backend health.
# SessionStart hook. Also runnable manually: bash .claude/hooks/check-dev-env.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

# Consume stdin (hook JSON payload)
cat > /dev/null 2>/dev/null || true

ISSUES=()

# --- Docker containers ---
cd "$PROJECT_DIR"

if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    REQUIRED_SVCS=("postgres" "minio" "redis" "mailpit")
    for svc in "${REQUIRED_SVCS[@]}"; do
        CID=$(docker compose ps --status running -q "$svc" 2>/dev/null || true)
        if [ -z "$CID" ]; then
            ISSUES+=("  - $svc is not running")
        fi
    done

    if [ ${#ISSUES[@]} -gt 0 ]; then
        {
            echo ""
            echo "--- DEV ENV CHECK: Docker services missing ---"
            for issue in "${ISSUES[@]}"; do echo "$issue"; done
            echo ""
            echo "Fix: docker compose up -d postgres minio redis mailpit minio-init"
            echo "---"
            echo ""
        } >&2
    fi
fi

# --- Backend health ---
if ! curl -sf --max-time 3 http://localhost:8000/health > /dev/null 2>&1; then
    {
        echo ""
        echo "--- DEV ENV CHECK: Backend not responding ---"
        echo "  curl http://localhost:8000/health failed"
        echo ""
        echo "Fix: mamba activate camis2026 && cd $PROJECT_DIR && uvicorn app.main:app --reload --port 8000"
        echo "---"
        echo ""
    } >&2
fi

exit 0
