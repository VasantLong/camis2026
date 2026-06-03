#!/usr/bin/env bash
# Full database reset: drop volumes, recreate, migrate, seed.
# Usage: bash scripts/db-reset.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== 1. dropping all Docker volumes ==="
docker compose down -v

echo "=== 2. starting core services ==="
docker compose up -d postgres minio redis
# wait for PG to be healthy
until docker compose exec -T postgres pg_isready -U docapp -d doc_metadata >/dev/null 2>&1; do
    sleep 1
done

echo "=== 3. creating MinIO bucket ==="
docker compose run --rm minio-init

echo "=== 4. running migrations ==="
alembic upgrade head

echo "=== 5. seeding test users ==="
python scripts/seed_test_users.py

echo "=== 6. seeding test activities ==="
python scripts/seed_test_activities.py

echo "=== 7. clearing Redis rate limits ==="
docker compose exec -T redis redis-cli -a secret_redis_pwd --scan --pattern "login_attempts:*" 2>/dev/null | \
    xargs -r docker compose exec -T redis redis-cli -a secret_redis_pwd DEL 2>/dev/null || true

echo ""
echo "=== done ==="
echo "Login: promoter@test.com / pass123"
echo "Other users: security@test.com, admin@test.com, superadmin@test.com, etc."
