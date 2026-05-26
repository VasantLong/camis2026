from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from app.auth import (
    check_login_blocked,
    create_access_token,
    create_email_change_token,
    create_refresh_token,
    hash_password,
    record_login_attempt,
    revoke_user_tokens,
    verify_email_change_token,
    verify_password,
    verify_refresh_token,
)
from app.database import get_db
from app.email import send_email_verification, send_welcome_email
from app.deps import get_current_user
from app.errors import ConflictError
from app.models.rbac import Permission, Role, RolePermission, RoleRequest, UserRole
from app.models.user import User
from app.schemas.role_request import RoleRequestCreate, RoleRequestResponse

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str


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
    permissions: list[str] = []
    roles: list[str] = []
    role_permissions: dict[str, list[str]] = {}
    pending_role_request: PendingRoleRequest | None = None


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, response: Response, bg: BackgroundTasks, db=Depends(get_db)):
    existing = await db.execute(
        select(User).where(User.email == body.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已注册")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(str(user.id))
    refresh = await create_refresh_token(db, str(user.id))
    response.set_cookie(
        key="refresh_token", value=refresh,
        httponly=True, secure=False, samesite="lax",
        max_age=7 * 24 * 3600, path="/",
    )
    bg.add_task(send_welcome_email, user.email, user.display_name)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, request: Request, db=Depends(get_db)):
    if await check_login_blocked(db, body.email):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="登录尝试过多，请15分钟后再试")

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        await record_login_attempt(db, body.email, False)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")

    await record_login_attempt(db, body.email, True)
    token = create_access_token(str(user.id))
    refresh = await create_refresh_token(db, str(user.id))
    response.set_cookie(
        key="refresh_token", value=refresh,
        httponly=True, secure=False, samesite="lax",
        max_age=7 * 24 * 3600, path="/",
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    # Query permissions with role name for grouping
    rp_result = await db.execute(
        select(Role.name, Permission.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(UserRole.user_id == current_user.id)
        .order_by(Role.name)
    )
    role_perms: dict[str, list[str]] = {}
    perm_set: set[str] = set()
    for role_name, perm_name in rp_result.all():
        role_perms.setdefault(role_name, []).append(perm_name)
        perm_set.add(perm_name)
    permissions = list(perm_set)

    role_result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == current_user.id)
    )
    roles = [row[0] for row in role_result.all()]

    pending_rr = None
    rr_result = await db.execute(
        select(RoleRequest, Role.name)
        .join(Role, Role.id == RoleRequest.role_id)
        .where(
            RoleRequest.user_id == current_user.id,
            RoleRequest.status == "pending",
        )
        .order_by(RoleRequest.created_at.desc())
        .limit(1)
    )
    row = rr_result.first()
    if row:
        rr, role_name = row
        pending_rr = PendingRoleRequest(
            id=str(rr.id),
            role_id=str(rr.role_id),
            role_name=role_name,
            status=rr.status,
            created_at=rr.created_at.isoformat(),
        )

    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        display_name=current_user.display_name,
        is_active=current_user.is_active,
        permissions=permissions,
        roles=roles,
        role_permissions=role_perms,
        pending_role_request=pending_rr,
    )


class UpdateProfileRequest(BaseModel):
    display_name: str


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    current_user.display_name = body.display_name
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    # Reuse the same response building logic (simplified inline)
    from app.models.rbac import Permission, Role, RolePermission, RoleRequest, UserRole
    rp_result = await db.execute(
        select(Role.name, Permission.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(UserRole.user_id == current_user.id)
        .order_by(Role.name)
    )
    role_perms: dict[str, list[str]] = {}
    perm_set: set[str] = set()
    for role_name, perm_name in rp_result.all():
        role_perms.setdefault(role_name, []).append(perm_name)
        perm_set.add(perm_name)

    role_result = await db.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == current_user.id)
    )
    roles = [row[0] for row in role_result.all()]

    pending_rr = None
    rr_result = await db.execute(
        select(RoleRequest, Role.name)
        .join(Role, Role.id == RoleRequest.role_id)
        .where(RoleRequest.user_id == current_user.id, RoleRequest.status == "pending")
        .order_by(RoleRequest.created_at.desc()).limit(1)
    )
    row = rr_result.first()
    if row:
        rr, role_name = row
        pending_rr = PendingRoleRequest(
            id=str(rr.id), role_id=str(rr.role_id), role_name=role_name,
            status=rr.status, created_at=rr.created_at.isoformat(),
        )

    return UserResponse(
        id=str(current_user.id), email=current_user.email,
        display_name=current_user.display_name, is_active=current_user.is_active,
        permissions=list(perm_set), roles=roles,
        role_permissions=role_perms, pending_role_request=pending_rr,
    )


class EmailChangeRequest(BaseModel):
    new_email: EmailStr


@router.post("/me/email-change", status_code=202)
async def request_email_change(
    body: EmailChangeRequest,
    bg: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    # Check new email not already in use
    existing = await db.execute(select(User).where(User.email == body.new_email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已被注册")

    token = create_email_change_token(str(current_user.id), body.new_email)
    verify_url = f"http://localhost:8000/auth/verify-email?token={token}"
    bg.add_task(send_email_verification, body.new_email, verify_url)
    return {"message": "验证邮件已发送至新邮箱，请查收"}


@router.get("/verify-email")
async def verify_email(token: str = Query(...), db=Depends(get_db)):
    try:
        payload = verify_email_change_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证链接无效或已过期")

    user_id = payload.get("sub")
    new_email = payload.get("email")
    if not user_id or not new_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证链接无效")

    # Check email not taken by another user
    existing = await db.execute(select(User).where(User.email == new_email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已被注册")

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    user.email = new_email
    db.add(user)
    await db.commit()

    return RedirectResponse(url="http://localhost:5173/profile")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(response: Response, refresh_token: str = Cookie(None), db=Depends(get_db)):
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")
    token_record = await verify_refresh_token(db, refresh_token)
    if token_record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    token_record.revoked = True
    db.add(token_record)
    await db.commit()

    user = await db.get(User, token_record.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access = create_access_token(str(user.id))
    new_refresh = await create_refresh_token(db, str(user.id))
    response.set_cookie(
        key="refresh_token", value=new_refresh,
        httponly=True, secure=False, samesite="lax",
        max_age=7 * 24 * 3600, path="/",
    )
    return TokenResponse(access_token=access)


@router.post("/logout")
async def logout(response: Response, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    await revoke_user_tokens(db, str(current_user.id))
    response.delete_cookie("refresh_token", path="/")
    return {"message": "已登出"}


class RoleOption(BaseModel):
    id: str
    name: str
    label: str


@router.get("/roles", response_model=list[RoleOption])
async def list_roles(db=Depends(get_db)):
    result = await db.execute(
        select(Role).where(Role.name != "SuperAdmin").order_by(Role.name)
    )
    roles = result.scalars().all()
    label_map = {
        "SuperAdmin": "超级管理员",
        "Promoter": "宣策部",
        "SecurityOfficer": "安保部",
        "AdminStaff": "行政部",
        "AdminManager": "行政部负责人",
        "SecurityManager": "安保部负责人",
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
    db=Depends(get_db),
):
    existing = await db.execute(
        select(RoleRequest).where(
            RoleRequest.user_id == current_user.id,
            RoleRequest.status == "pending",
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError("您已有待审批的角色申请")

    role = await db.get(Role, body.role_id)
    if role is None:
        from app.errors import NotFoundError
        raise NotFoundError("角色不存在")
    if role.name == "SuperAdmin":
        from app.errors import ForbiddenError
        raise ForbiddenError("不能申请超级管理员角色")

    rr = RoleRequest(user_id=current_user.id, role_id=body.role_id)
    db.add(rr)
    await db.commit()
    await db.refresh(rr)

    return RoleRequestResponse(
        id=rr.id,
        user_id=rr.user_id,
        role_id=rr.role_id,
        role_name=role.name,
        status=rr.status,
        created_at=rr.created_at,
    )
