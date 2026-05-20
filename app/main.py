from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.routers import health
from app.services.minio_client import check_bucket, minio_client
from app.services.redis_client import close_redis, get_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    await check_bucket()
    redis = await get_redis()
    await redis.ping()
    await close_redis()
    yield
    await engine.dispose()


app = FastAPI(title="CAMIS API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
