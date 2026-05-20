from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.database import async_session
from app.services.minio_client import minio_client
from app.services.redis_client import get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    checks = {"postgres": "error", "minio": "error", "redis": "error"}

    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = str(e)

    try:
        if minio_client.bucket_exists(settings.minio_bucket):
            checks["minio"] = "ok"
        else:
            checks["minio"] = "bucket_not_found"
    except Exception as e:
        checks["minio"] = str(e)

    try:
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = str(e)

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "ok" if all_ok else "degraded", "checks": checks}
