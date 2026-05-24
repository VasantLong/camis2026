"""业务异常与统一错误响应格式。"""

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """所有业务异常的基类。"""
    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, detail: str = "", fields: dict[str, str] | None = None):
        self.detail = detail
        self.fields = fields or {}


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"


class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    body = {"detail": exc.detail, "code": exc.code}
    if exc.fields:
        body["fields"] = exc.fields
    return JSONResponse(status_code=exc.status_code, content=body)
