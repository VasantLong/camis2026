import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.errors import AppError, app_error_handler
from app.logging_config import setup_logging
from app.middleware import RequestIDMiddleware
from app.routers import activities, admin, auth, dashboard, documents, filings, health, workflows
from app.services.minio_client import check_bucket, minio_client
from app.services.redis_client import close_redis, get_redis

setup_logging()
logger = logging.getLogger("camis")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup: checking MinIO bucket...")
    await check_bucket()
    redis = await get_redis()
    await redis.ping()
    logger.info("startup: Redis ok, closing startup connection")
    await close_redis()
    yield
    await engine.dispose()


app = FastAPI(title="CAMIS API", version="0.13.0", lifespan=lifespan)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allow_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(activities.router)
app.include_router(workflows.router)
app.include_router(filings.router)
app.include_router(dashboard.router)
app.include_router(admin.router)

app.add_exception_handler(AppError, app_error_handler)
