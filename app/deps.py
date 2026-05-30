from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.auth import decode_access_token
from app.database import get_db
from app.models.user import User

security = HTTPBearer()


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if user.is_archived:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该账号已被归档")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该账号已被禁用")
    token_email = payload.get("email")
    if token_email and token_email != user.email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱已更改，请用新邮箱重新登录")
    return user
