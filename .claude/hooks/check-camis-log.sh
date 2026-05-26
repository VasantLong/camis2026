#!/usr/bin/env bash
# Incremental camis log checker — reports new ERROR/WARNING lines since last check.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
LOG_FILE="$PROJECT_DIR/logs/camis.log"
POS_FILE="$PROJECT_DIR/.claude/log-check-position.txt"
LOCK_FILE="$POS_FILE.lock"

# Consume stdin (hook JSON payload) to prevent broken pipe
cat > /dev/null 2>/dev/null || true

# Non-blocking lock; skip if another instance is running
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    exit 0
fi

# Log file must exist
if [ ! -f "$LOG_FILE" ]; then
    exit 0
fi

CURRENT_LINES=$(wc -l < "$LOG_FILE")

if [ ! -f "$POS_FILE" ]; then
    echo "$CURRENT_LINES" > "$POS_FILE"
    exit 0
fi

LAST_CHECKED=$(cat "$POS_FILE")

# Validate LAST_CHECKED is a positive integer; reset on corruption
if ! [[ "$LAST_CHECKED" =~ ^[0-9]+$ ]]; then
    LAST_CHECKED=0
fi

# Reset if log rotated/shrunk
if [ "$LAST_CHECKED" -gt "$CURRENT_LINES" ]; then
    echo "$CURRENT_LINES" > "$POS_FILE"
    exit 0
fi

NEW_START=$((LAST_CHECKED + 1))

if [ "$NEW_START" -gt "$CURRENT_LINES" ]; then
    exit 0
fi

NEW_ISSUES=$(tail -n +"$NEW_START" "$LOG_FILE" | grep -n -wE 'ERROR|WARNING|CRITICAL' || true)

# Always update position so we don't re-scan
echo "$CURRENT_LINES" > "$POS_FILE"

if [ -z "$NEW_ISSUES" ]; then
    exit 0
fi

COUNT=$(echo "$NEW_ISSUES" | wc -l)

{
    echo ""
    echo "--- CAMIS LOG: $COUNT new issue(s) since last check ---"
    echo "$NEW_ISSUES"
    echo "--- end ---"
    echo "Run /camis-log-analyzer for deep analysis."
    echo ""
} >&2

exit 0
