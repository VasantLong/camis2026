from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr

from app.auth import check_login_blocked, record_login_failure, record_login_attempt
from app.database import get_db
from app.deps import get_current_user
from app.email import send_email_verification, send_welcome_email
from app.errors import ConflictError
from app.models.rbac import Role
from app.models.user import User
from app.schemas.role_request import RoleRequestCreate, RoleRequestResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _service(db=Depends(get_db)) -> AuthService:
    return AuthService(db)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str
    contact_phone: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PendingRoleRequest(BaseModel):
    id: str
    role_id: str
    role_name: str
    status: str
    created_at: str


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    is_active: bool
    contact_phone: str | None = None
    permissions: list[str] = []
    roles: list[str] = []
    role_permissions: dict[str, list[str]] = {}
    pending_role_request: PendingRoleRequest | None = None


class UpdateProfileRequest(BaseModel):
    display_name: str
    contact_phone: str | None = None


class EmailChangeRequest(BaseModel):
    new_email: EmailStr


class RoleOption(BaseModel):
    id: str
    name: str
    label: str


# ── Registration & Login ──


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, response: Response, bg: BackgroundTasks,
                   svc: AuthService = Depends(_service)):
    try:
        user = await svc.register_user(body.email, body.password, body.display_name, body.contact_phone)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    access, refresh = await svc.create_session(user)
    response.set_cookie(key="refresh_token", value=refresh,
                        httponly=True, secure=False, samesite="lax",
                        max_age=7 * 24 * 3600, path="/")
    bg.add_task(send_welcome_email, user.email, user.display_name)
    return TokenResponse(access_token=access)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, request: Request,
                svc: AuthService = Depends(_service)):
    if await check_login_blocked(body.email):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="登录尝试过多，请15分钟后再试")

    try:
        user = await svc.authenticate_user(body.email, body.password)
    except ValueError:
        await record_login_failure(body.email)
        await record_login_attempt(svc.db, body.email, False)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    await record_login_attempt(svc.db, body.email, True)
    access, refresh = await svc.create_session(user)
    response.set_cookie(key="refresh_token", value=refresh,
                        httponly=True, secure=False, samesite="lax",
                        max_age=7 * 24 * 3600, path="/")
    return TokenResponse(access_token=access)


# ── Current User ──


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user),
             svc: AuthService = Depends(_service)):
    profile = await svc.get_user_profile(current_user)
    return UserResponse(**profile)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    svc: AuthService = Depends(_service),
):
    await svc.update_profile(current_user, body.display_name, body.contact_phone)
    profile = await svc.get_user_profile(current_user)
    return UserResponse(**profile)


# ── Email Change ──


@router.post("/me/email-change", status_code=202)
async def request_email_change(
    body: EmailChangeRequest,
    bg: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    svc: AuthService = Depends(_service),
):
    try:
        token = await svc.request_email_change(current_user, body.new_email)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    verify_url = f"http://localhost:8000/auth/verify-email?token={token}"
    bg.add_task(send_email_verification, body.new_email, verify_url)
    return {"message": "验证邮件已发送至新邮箱，请查收"}


@router.get("/verify-email")
async def verify_email(token: str = Query(...), svc: AuthService = Depends(_service)):
    try:
        await svc.verify_and_apply_email_change(token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return RedirectResponse(url="http://localhost:5173/login?verified=1")


# ── Token Refresh ──


@router.post("/refresh", response_model=TokenResponse)
async def refresh(response: Response, refresh_token: str = Cookie(None),
                  svc: AuthService = Depends(_service)):
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")
    try:
        user, access, new_refresh = await svc.refresh_session(refresh_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    except LookupError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    response.set_cookie(key="refresh_token", value=new_refresh,
                        httponly=True, secure=False, samesite="lax",
                        max_age=7 * 24 * 3600, path="/")
    return TokenResponse(access_token=access)


@router.post("/logout")
async def logout(response: Response, current_user: User = Depends(get_current_user),
                 svc: AuthService = Depends(_service)):
    await svc.revoke_session(current_user.id)
    response.delete_cookie("refresh_token", path="/")
    return {"message": "已登出"}


# ── Roles ──


@router.get("/roles", response_model=list[RoleOption])
async def list_roles(svc: AuthService = Depends(_service)):
    roles = await svc.list_available_roles()
    label_map = {
        "SuperAdmin": "超级管理员", "Promoter": "宣策部",
        "SecurityOfficer": "安保部", "AdminStaff": "行政部",
        "AdminManager": "行政部负责人", "SecurityManager": "安保部负责人",
        "GovLiaison": "政府对接",
    }
    return [
        RoleOption(id=str(r.id), name=r.name, label=label_map.get(r.name, r.name))
        for r in roles
    ]


@router.post("/me/role-request", response_model=RoleRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_role(
    body: RoleRequestCreate,
    current_user: User = Depends(get_current_user),
    svc: AuthService = Depends(_service),
):
    try:
        rr = await svc.submit_role_request(current_user.id, body.role_id)
    except ValueError as e:
        raise ConflictError(str(e))
    except LookupError as e:
        from app.errors import NotFoundError
        raise NotFoundError(str(e))
    except PermissionError as e:
        from app.errors import ForbiddenError
        raise ForbiddenError(str(e))

    role = await svc.db.get(Role, rr.role_id)
    return RoleRequestResponse(
        id=rr.id, user_id=rr.user_id, role_id=rr.role_id,
        role_name=role.name if role else "", status=rr.status,
        created_at=rr.created_at,
    )
