import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.errors import AppError, app_error_handler
from app.logging_config import setup_logging
from app.middleware import RequestIDMiddleware
from app.routers import activities, admin, auth, dashboard, documents, filings, health, notifications, templates, workflows
from app.services.minio_client import check_bucket, minio_client
from app.services.redis_client import close_redis, get_redis

setup_logging()
logger = logging.getLogger("camis")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup: checking MinIO bucket...")
    await check_bucket()
    redis = await get_redis()
    if redis:
        logger.info("startup: Redis ok")
    else:
        logger.warning("startup: Redis unavailable — caching disabled")
    await close_redis()
    yield
    await engine.dispose()


app = FastAPI(title="CAMIS API", version="0.23.0", lifespan=lifespan)

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
app.include_router(templates.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(notifications.router)

app.add_exception_handler(AppError, app_error_handler)


from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    field_names = {"name": "活动名称", "type": "活动类型", "estimated_time": "预计举办时间",
                   "location": "举办地点", "sponsor": "主办方", "sponsor_contact": "主办方联系人",
                   "sponsor_phone": "主办方联系方式", "deadline": "截止日期", "designer_id": "方案编制人"}
    msgs = []
    for err in exc.errors():
        loc = err["loc"][-1] if err["loc"] else "?"
        field = field_names.get(str(loc), str(loc))
        msg = err.get("msg", "").replace("field required", "必填").replace("ensure this value has at least", "至少需要")
        msgs.append(f"{field}: {msg}")
    return JSONResponse(status_code=422, content={"detail": "; ".join(msgs)})
