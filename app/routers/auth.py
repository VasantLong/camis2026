from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from app.auth import (
    check_login_blocked,
    create_access_token,
    create_refresh_token,
    hash_password,
    record_login_attempt,
    revoke_user_tokens,
    verify_password,
    verify_refresh_token,
)
from app.database import get_db
from app.deps import get_current_user
from app.errors import ConflictError
from app.models.rbac import Permission, Role, RolePermission, RoleRequest, UserRole
from app.models.user import User
from app.schemas.role_request import RoleRequestCreate, RoleRequestResponse

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    display_name: str | None = None


class LoginRequest(BaseModel):
    username: str
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
    username: str
    email: str
    display_name: str | None
    is_active: bool
    permissions: list[str] = []
    roles: list[str] = []
    pending_role_request: PendingRoleRequest | None = None


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db=Depends(get_db)):
    existing = await db.execute(
        select(User).where((User.username == body.username) | (User.email == body.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists")
    user = User(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(str(user.id), user.username)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, request: Request, db=Depends(get_db)):
    if await check_login_blocked(db, body.username):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="登录尝试过多，请15分钟后再试")

    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        await record_login_attempt(db, body.username, False)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    await record_login_attempt(db, body.username, True)
    token = create_access_token(str(user.id), user.username)
    refresh = await create_refresh_token(db, str(user.id))
    response.set_cookie(
        key="refresh_token", value=refresh,
        httponly=True, secure=False, samesite="lax",
        max_age=7 * 24 * 3600, path="/",
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    perm_result = await db.execute(
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == current_user.id)
    )
    permissions = [row[0] for row in perm_result.all()]

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
        username=current_user.username,
        email=current_user.email,
        display_name=current_user.display_name,
        is_active=current_user.is_active,
        permissions=permissions,
        roles=roles,
        pending_role_request=pending_rr,
    )


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

    access = create_access_token(str(user.id), user.username)
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
