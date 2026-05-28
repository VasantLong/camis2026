import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.auth import RefreshToken

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
REFRESH_TOKEN_DAYS = 7


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


EMAIL_CHANGE_EXPIRE_MINUTES = 15


def create_email_change_token(user_id: str, new_email: str) -> str:
    payload = {
        "sub": user_id,
        "email": new_email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=EMAIL_CHANGE_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_email_change_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def create_refresh_token(db: AsyncSession, user_id: str) -> str:
    raw = secrets.token_urlsafe(48)
    token = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS),
    )
    db.add(token)
    await db.commit()
    return raw


async def verify_refresh_token(db: AsyncSession, raw: str) -> RefreshToken | None:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == _hash_token(raw),
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    return result.scalar_one_or_none()


async def revoke_user_tokens(db: AsyncSession, user_id: str) -> None:
    from sqlalchemy import update
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked == False)
        .values(revoked=True)
    )
    await db.commit()


async def check_login_blocked(login_id: str) -> bool:
    from app.services.redis_client import get_redis

    redis = await get_redis()
    key = f"login_attempts:{login_id}"
    count = await redis.get(key)
    return int(count or 0) >= MAX_LOGIN_ATTEMPTS


async def record_login_failure(login_id: str) -> None:
    from app.services.redis_client import get_redis

    redis = await get_redis()
    key = f"login_attempts:{login_id}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, LOCKOUT_MINUTES * 60)


async def record_login_attempt(db: AsyncSession, login_id: str, success: bool) -> None:
    from sqlalchemy import text
    await db.execute(
        text("INSERT INTO login_attempts (login_id, success) VALUES (:l, :s)"),
        {"l": login_id, "s": success},
    )
    await db.commit()
