"""创建预设测试活动，覆盖 12 种状态 + 附件 + 完整属性。幂等。"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.auth import hash_password
from app.database import async_session
from app.models.activity import (
    Activity, ActivityPlan, ActivityStatusLog, ApprovalRecord,
    ImplementationRecord, SecurityPlan,
)
from app.models.document import Document
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.services.minio_client import upload_file

# ── activity definitions ──
# (name, type, location, sponsor, estimated_days, deadline_days, target_status)
# days > 0 = future, days < 0 = past, days = 0 = today
ACTIVITIES = [
    ("2026 校园文化节",     "大型", "体育馆",   "校团委",  30, 20, "待设计方案"),
    ("安全生产月启动仪式",  "大型", "会议中心", "安监局",  25, 15, "待安保方案设计"),
    ("社区志愿服务日",      "小型", "市民广场", "街道办",  20, 10, "待备案申请"),
    ("年度总结表彰大会",    "大型", "大礼堂",   "总工会",  15,  5, "备案材料已交接"),
    ("网络安全培训讲座",    "中型", "报告厅",   "网信办",  10,  3, "审批通过"),
    ("职工运动会",          "大型", "体育场",   "工会",     7,  1, "审批通过-待举办"),
    ("春节联欢晚会",        "大型", "文化宫",   "文化局",   0,-10, "举办中"),
    ("科普进社区活动",      "小型", "社区中心", "科协",    -5,-15, "已结束"),
    ("法治宣传周活动",      "中型", "法治广场", "司法局",   8, -2, "待补充备案材料"),
    ("青年创新创业大赛",    "大型", "会展中心", "人社局", -10,-20, "不通过/已终止"),
    ("绿色环保公益行",      "小型", "滨江公园", "环保局",   5, -2, "已取消"),
    ("全民读书月活动",      "中型", "图书馆",   "文化局",  60, -5, "已延期"),
]

# which sub-records each target status needs
STATUS_NEEDS = {
    "待设计方案":        [],
    "待安保方案设计":     ["plan"],
    "待备案申请":        ["plan", "security_plan"],
    "备案材料已交接":     ["plan", "security_plan"],
    "审批通过":          ["plan", "security_plan", "approval"],
    "审批通过-待举办":    ["plan", "security_plan", "approval"],
    "举办中":            ["plan", "security_plan", "approval"],
    "已结束":            ["plan", "security_plan", "approval"],
    "待补充备案材料":     ["plan", "security_plan", "approval"],
    "不通过/已终止":      ["plan", "security_plan", "approval"],
    "已取消":            ["plan"],
    "已延期":            ["plan"],
}


async def seed():
    async with async_session() as db:
        # ── ensure users ──
        promoter = await _ensure_user(db, "promoter", "promoter@test.com", ["Promoter"])
        security = await _ensure_user(db, "security", "security@test.com",
                                       ["SecurityOfficer", "SecurityManager"])
        liaison = await _ensure_user(db, "liaison", "liaison@test.com", ["GovLiaison"])

        # ── check existing ──
        names = [a[0] for a in ACTIVITIES]
        existing = await db.execute(select(Activity).where(Activity.name.in_(names)))
        if existing.scalars().all():
            print("skip: activities already seeded")
            return

        now = datetime.now(timezone.utc)

        for name, atype, location, sponsor, est_days, dl_days, target in ACTIVITIES:
            estimated = now + timedelta(days=est_days)
            deadline = now + timedelta(days=dl_days)

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

            needs = STATUS_NEEDS.get(target, [])

            if "plan" in needs:
                plan_text = f"《{name}》活动方案\n主办方：{sponsor}\n地点：{location}\n类型：{atype}"
                plan_bytes = plan_text.encode("utf-8")
                plan_path = f"activities/{activity.id}/{uuid4().hex}.txt"
                await upload_file(plan_path, plan_bytes, "text/plain; charset=utf-8")

                _add_doc(db, activity.id, promoter.id,
                         f"{name}_活动方案.txt", plan_path,
                         len(plan_bytes), "text/plain; charset=utf-8", ["方案"])

                db.add(ActivityPlan(
                    activity_id=activity.id,
                    content=plan_text,
                    attachment_url=plan_path,
                    submit_time=now,
                    designer_id=promoter.id,
                    is_overdue=False,
                ))
                await db.flush()

            if "security_plan" in needs:
                sec_text = f"《{name}》安保方案\n风险等级：一般"
                sec_bytes = sec_text.encode("utf-8")
                sec_path = f"activities/{activity.id}/{uuid4().hex}.txt"
                await upload_file(sec_path, sec_bytes, "text/plain; charset=utf-8")

                _add_doc(db, activity.id, security.id,
                         f"{name}_安保方案.txt", sec_path,
                         len(sec_bytes), "text/plain; charset=utf-8", ["安保"])

                db.add(SecurityPlan(
                    activity_id=activity.id,
                    risk_level="一般",
                    audit_status="已审核",
                    manager_id=security.id,
                    sign_time=now,
                ))
                await db.flush()

            if "approval" in needs:
                approval_status = "approved"
                opinion = None
                if target == "待补充备案材料":
                    approval_status = "rectification"
                    opinion = "材料不完整，请补充活动预算明细和消防验收证明"
                elif target == "不通过/已终止":
                    approval_status = "rejected"
                    opinion = "活动方案不符合相关规定，不予批准"

                approval_path = None
                if approval_status == "approved":
                    appr_text = f"《{name}》政府批文\n批准举办"
                    appr_bytes = appr_text.encode("utf-8")
                    approval_path = f"activities/{activity.id}/{uuid4().hex}.txt"
                    await upload_file(approval_path, appr_bytes, "text/plain; charset=utf-8")

                    _add_doc(db, activity.id, liaison.id,
                             f"{name}_政府批文.txt", approval_path,
                             len(appr_bytes), "text/plain; charset=utf-8", ["批文"])

                db.add(ApprovalRecord(
                    activity_id=activity.id,
                    liaison_id=liaison.id,
                    approval_status=approval_status,
                    attachment_url=approval_path,
                    approval_date=now if approval_status == "approved" else None,
                    rectification_opinion=opinion,
                ))
                await db.flush()

            # ── set final status via transitions ──
            from app.services.workflow_service import WorkflowService
            wf = WorkflowService(db)

            PATH: dict[str, list[str]] = {
                "待设计方案":        [],
                "待安保方案设计":     ["待安保方案设计"],
                "待备案申请":        ["待安保方案设计", "待备案申请"],
                "备案材料已交接":     ["待安保方案设计", "待备案申请", "备案材料已交接"],
                "审批通过":          ["待安保方案设计", "待备案申请", "备案材料已交接", "审批通过"],
                "审批通过-待举办":    ["待安保方案设计", "待备案申请", "备案材料已交接", "审批通过", "审批通过-待举办"],
                "举办中":            ["待安保方案设计", "待备案申请", "备案材料已交接", "审批通过", "审批通过-待举办", "举办中"],
                "已结束":            ["待安保方案设计", "待备案申请", "备案材料已交接", "审批通过", "审批通过-待举办", "举办中", "已结束"],
                "待补充备案材料":     ["待安保方案设计", "待备案申请", "备案材料已交接", "待补充备案材料"],
                "不通过/已终止":      ["待安保方案设计", "待备案申请", "备案材料已交接", "不通过/已终止"],
                "已取消":            [],
                "已延期":            [],
            }

            path = PATH[target]
            for to_status in path:
                await wf.transition(activity.id, to_status, security)

            # force-cancel / force-postpone
            if target in ("已取消", "已延期") and activity.status == "待设计方案":
                db.add(ActivityStatusLog(
                    activity_id=activity.id,
                    from_status="待设计方案",
                    to_status=target,
                    operator_id=security.id,
                    comment="测试强制变更",
                ))
                db.add(ImplementationRecord(
                    activity_id=activity.id,
                    admin_id=security.id,
                    change_status=target,
                    change_reason="测试强制变更",
                    archived_at=now,
                ))
                activity.status = target

            await db.commit()
            print(f"created: {name} → {target}")

    print("done")


def _add_doc(db, activity_id, uploader_id, filename, minio_path, file_size, content_type, tags=None):
    db.add(Document(
        activity_id=activity_id,
        uploader_id=uploader_id,
        filename=filename,
        minio_path=minio_path,
        file_size=file_size,
        content_type=content_type,
        tags=tags or [],
    ))


async def _ensure_user(db, username, email, role_names):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user:
        return user
    role_result = await db.execute(select(Role).where(Role.name.in_(role_names)))
    roles = role_result.scalars().all()
    user = User(
        username=username,
        email=email,
        password_hash=hash_password("pass123"),
        display_name=username,
    )
    db.add(user)
    await db.flush()
    for role in roles:
        db.add(UserRole(user_id=user.id, role_id=role.id))
    await db.commit()
    await db.refresh(user)
    return user


if __name__ == "__main__":
    asyncio.run(seed())
