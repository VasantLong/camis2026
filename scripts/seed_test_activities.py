"""创建预设测试活动，覆盖 10 种状态。幂等，可重复执行。"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.auth import hash_password
from app.database import async_session
from app.models.activity import Activity
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.schemas.activity import ActivityCreate

ACTIVITIES = [
    # (name, type, location, sponsor, days_ahead, target_status)
    ("2026 校园文化节", "大型", "体育馆", "校团委", 10, "待设计方案"),
    ("安全生产月启动仪式", "大型", "会议中心", "安监局", 12, "待安保方案设计"),
    ("社区志愿服务日", "小型", "市民广场", "街道办", 8, "待备案申请"),
    ("年度总结表彰大会", "大型", "大礼堂", "总工会", 20, "备案材料已交接"),
    ("网络安全培训讲座", "中型", "报告厅", "网信办", 5, "审批通过"),
    ("职工运动会", "大型", "体育场", "工会", 15, "审批通过-待举办"),
    ("春节联欢晚会", "大型", "文化宫", "文化局", 25, "待补充备案材料"),
    ("法治宣传周活动", "中型", "法治广场", "司法局", 3, "不通过/已终止"),
    ("科普进社区活动", "小型", "社区中心", "科协", 2, "已取消"),
    ("青年创新创业大赛", "大型", "会展中心", "人社局", 18, "已延期"),
]

# transition paths to reach each target status
STATUS_PATH: dict[str, list[str]] = {
    "待设计方案":        [],
    "待安保方案设计":     ["待安保方案设计"],
    "待备案申请":        ["待安保方案设计", "待备案申请"],
    "备案材料已交接":     ["待安保方案设计", "待备案申请", "备案材料已交接"],
    "审批通过":          ["待安保方案设计", "待备案申请", "备案材料已交接", "审批通过"],
    "审批通过-待举办":    ["待安保方案设计", "待备案申请", "备案材料已交接", "审批通过", "审批通过-待举办"],
    "待补充备案材料":     ["待安保方案设计", "待备案申请", "备案材料已交接", "待补充备案材料"],
    "不通过/已终止":      ["待安保方案设计", "待备案申请", "备案材料已交接", "不通过/已终止"],
    "已取消":            [],
    "已延期":            [],
}


async def seed():
    async with async_session() as db:
        # ── ensure promoter user ──
        result = await db.execute(select(User).where(User.username == "promoter"))
        promoter = result.scalar_one_or_none()
        if promoter is None:
            role_result = await db.execute(select(Role).where(Role.name == "Promoter"))
            promoter_role = role_result.scalar_one()
            promoter = User(
                username="promoter",
                email="promoter@test.com",
                password_hash=hash_password("pass123"),
                display_name="promoter",
            )
            db.add(promoter)
            await db.flush()
            db.add(UserRole(user_id=promoter.id, role_id=promoter_role.id))
            await db.commit()
            await db.refresh(promoter)

        # ── ensure security user ──
        result = await db.execute(select(User).where(User.username == "security"))
        security = result.scalar_one_or_none()
        if security is None:
            role_result = await db.execute(
                select(Role).where(Role.name.in_(["SecurityOfficer", "SecurityManager"]))
            )
            sec_roles = role_result.scalars().all()
            security = User(
                username="security",
                email="security@test.com",
                password_hash=hash_password("pass123"),
                display_name="security",
            )
            db.add(security)
            await db.flush()
            for role in sec_roles:
                db.add(UserRole(user_id=security.id, role_id=role.id))
            await db.commit()
            await db.refresh(security)

        # ── check if already seeded ──
        existing = await db.execute(
            select(Activity).where(Activity.name.in_([a[0] for a in ACTIVITIES]))
        )
        if existing.scalars().all():
            print("skip: activities already seeded")
            return

        now = datetime.now(timezone.utc)

        for name, atype, location, sponsor, days_ahead, target_status in ACTIVITIES:
            estimated = now + timedelta(days=days_ahead)
            deadline = now + timedelta(days=max(1, days_ahead - 3))

            activity = Activity(
                name=name,
                type=atype,
                estimated_time=estimated,
                location=location,
                sponsor=sponsor,
                deadline=deadline,
                status="待设计方案",
                owner_id=promoter.id,
                designer_id=promoter.id,
            )
            db.add(activity)
            await db.flush()

            path = STATUS_PATH.get(target_status, [])
            current = "待设计方案"

            from app.models.activity import ActivityStatusLog

            for to_status in path:
                from app.services.workflow_service import WorkflowService
                wf = WorkflowService(db)
                try:
                    log = await wf.transition(activity.id, to_status, security)
                    current = to_status
                except (ValueError, LookupError) as e:
                    print(f"  skip transition {current}→{to_status}: {e}")

            # force-cancel / force-postpone as admin
            if target_status in ("已取消", "已延期") and current == "待设计方案":
                from app.models.activity import ActivityStatusLog, ImplementationRecord
                activity.status = target_status
                db.add(ActivityStatusLog(
                    activity_id=activity.id,
                    from_status="待设计方案",
                    to_status=target_status,
                    operator_id=security.id,
                    comment="测试强制变更",
                ))
                db.add(ImplementationRecord(
                    activity_id=activity.id,
                    admin_id=security.id,
                    change_status=target_status,
                    change_reason="测试强制变更",
                    archived_at=now,
                ))

            await db.commit()
            print(f"created: {name} → {target_status}")

    print("done")


if __name__ == "__main__":
    asyncio.run(seed())
