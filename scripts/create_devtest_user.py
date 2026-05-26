"""Create a devtest user with all roles for development testing.
Run: python scripts/create_devtest_user.py
If user exists, updates roles (adds any missing)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import asyncio
from sqlalchemy import select
from app.database import async_session
from app.models.user import User
from app.models.rbac import Role, UserRole
from app.auth import hash_password

DEV_EMAIL = "devtest@test.com"
DEV_PASSWORD = "pass123"


async def main():
    async with async_session() as db:
        # Get or create user
        result = await db.execute(select(User).where(User.email == DEV_EMAIL))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                email=DEV_EMAIL,
                password_hash=hash_password(DEV_PASSWORD),
                display_name="DevTest",
            )
            db.add(user)
            await db.flush()
            print(f"Created user: {DEV_EMAIL}")
        else:
            print(f"User exists: {DEV_EMAIL}")

        # Get all roles
        roles_result = await db.execute(select(Role))
        all_roles = roles_result.scalars().all()

        # Get existing user roles
        existing_result = await db.execute(
            select(UserRole.role_id).where(UserRole.user_id == user.id)
        )
        existing_role_ids = {row[0] for row in existing_result.all()}

        # Assign missing roles
        added = 0
        for role in all_roles:
            if role.id not in existing_role_ids:
                db.add(UserRole(user_id=user.id, role_id=role.id))
                added += 1
                print(f"  + {role.name}")

        await db.commit()
        if added:
            print(f"Assigned {added} new role(s)")
        else:
            print("All roles already assigned")
        print(f"Total: {len(all_roles)} roles, user={DEV_EMAIL} / {DEV_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
