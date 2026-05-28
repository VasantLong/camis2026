"""创建预设测试用户。幂等，可重复执行。"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.auth import hash_password
from app.database import async_session
from app.models.rbac import Role, UserRole
from app.models.user import User

SEED_USERS = [
    ("superadmin@test.com", "pass123", ["SuperAdmin"]),
    ("promoter@test.com", "pass123", ["Promoter"]),
    ("security@test.com", "pass123", ["SecurityOfficer", "SecurityManager"]),
    ("admin@test.com", "pass123", ["AdminStaff", "AdminManager"]),
    ("liaison@test.com", "pass123", ["GovLiaison"]),
    ("testuser@test.com", "test123", []),
]


async def seed():
    async with async_session() as db:
        for email, password, role_names in SEED_USERS:
            result = await db.execute(select(User).where(User.email == email))
            if result.scalar_one_or_none():
                print(f"skip: {email} (exists)")
                continue

            display = email.split("@")[0]
            user = User(
                email=email,
                password_hash=hash_password(password),
                display_name=display,
            )
            db.add(user)
            await db.flush()

            for role_name in role_names:
                role_result = await db.execute(select(Role).where(Role.name == role_name))
                role = role_result.scalar_one()
                db.add(UserRole(user_id=user.id, role_id=role.id))

            print(f"created: {email} roles={role_names}")

        await db.commit()
    print("done")


if __name__ == "__main__":
    asyncio.run(seed())
