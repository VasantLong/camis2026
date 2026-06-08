from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity, ActivityStatusLog
from app.models.user import User
from app.services.notification_service import NotificationService

TRANSITION_MATRIX: dict[str, set[str]] = {
    "待设计方案":     {"待安保方案设计"},
    "待安保方案设计":  {"待安保方案设计", "待备案申请"},
    "待备案申请":     {"备案材料已交接"},
    "备案材料已交接":  {"审批通过", "待补充备案材料", "不通过/已终止"},
    "待补充备案材料":  {"备案材料已交接"},
    "审批通过":       {"审批通过-待举办", "待安保方案设计"},
    "审批通过-待举办": {"举办中"},
    "举办中":         {"已结束"},
}

TERMINAL_STATUSES = {"已结束", "不通过/已终止", "已取消", "已延期"}

NOTIFICATION_RULES: dict[str, tuple[list[str], str]] = {
    "待安保方案设计":  (["SecurityOfficer"], "需进行安保方案设计"),
    "待备案申请":      (["SecurityOfficer"], "材料齐备，可开始备案申请"),
    "备案材料已交接":  (["GovLiaison"], "备案材料已流转至政府对接"),
    "审批通过":        (["SecurityManager"], "批文已上传，待安保部确认审批结果"),
    "审批通过-待举办": (["AdminStaff"], "活动批文已下发，可合法举办"),
    "待补充备案材料":  (["SecurityOfficer"], "需补充备案材料"),
    "不通过/已终止":   (["AdminStaff", "SecurityOfficer"], "活动审批未通过"),
}

REJECT_NOTIFY_ROLES = ["AdminStaff", "SecurityOfficer"]


class WorkflowService:
    def __init__(self, db: AsyncSession, notification: NotificationService | None = None):
        self.db = db
        self.notification = notification or NotificationService(db)

    def can_transition(self, from_status: str, to_status: str) -> bool:
        allowed = TRANSITION_MATRIX.get(from_status, set())
        return to_status in allowed

    async def transition(
        self, activity_id: UUID, to_status: str, operator: User, comment: str | None = None,
    ) -> ActivityStatusLog:
        activity = await self.db.get(Activity, activity_id)
        if activity is None:
            raise LookupError("活动不存在")

        if activity.status in TERMINAL_STATUSES:
            raise ValueError("活动已处于终态，无法变更状态")

        if activity.status == "待设计方案" and activity.designer_id:
            designer = await self.db.get(User, activity.designer_id)
            if designer and not designer.contact_phone:
                raise ValueError("编制人的联系方式为空，请先补充联系方式后再提交")

        if not self.can_transition(activity.status, to_status):
            raise ValueError(f"不允许从 {activity.status} 转换到 {to_status}")

        from_status = activity.status

        result = await self.db.execute(
            update(Activity)
            .where(Activity.id == activity_id, Activity.status == from_status)
            .values(status=to_status)
        )
        if result.rowcount == 0:
            raise ValueError("状态已被他人变更，请刷新后重试")

        log = ActivityStatusLog(
            activity_id=activity_id,
            from_status=from_status,
            to_status=to_status,
            operator_id=operator.id,
            comment=comment,
        )
        self.db.add(log)

        await self._update_security_plan(activity_id, from_status, to_status, operator)

        await self.db.commit()
        await self.db.refresh(log)

        rule = NOTIFICATION_RULES.get(to_status)
        if rule:
            roles, msg = rule
            for role_name in roles:
                await self.notification.notify_role(role_name, msg,
                    reference_id=activity_id, reference_type="activity")

        return log

    async def _update_security_plan(self, activity_id: UUID, from_status: str,
                                    to_status: str, operator: User) -> None:
        """Sync SecurityPlan.audit_status with workflow transitions."""
        if from_status == "待设计方案" and to_status == "待安保方案设计":
            from app.models.activity import SecurityPlan
            existing = await self.db.execute(
                select(SecurityPlan).where(SecurityPlan.activity_id == activity_id)
            )
            if not existing.scalar_one_or_none():
                self.db.add(SecurityPlan(
                    activity_id=activity_id,
                    audit_status="待编制",
                    risk_level=None,
                ))
            return

        from app.models.activity import SecurityPlan
        sp = await self.db.get(SecurityPlan, activity_id)
        if sp is None:
            return

        if from_status == "待安保方案设计":
            from app.models.rbac import Role, UserRole
            role_rows = await self.db.execute(
                select(Role.name).join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == operator.id)
            )
            roles = {row[0] for row in role_rows.all()}

            if to_status == "待安保方案设计":
                sp.audit_status = "待编制"
            elif to_status == "待备案申请":
                if "SecurityManager" in roles:
                    sp.audit_status = "已签署"
                    sp.manager_id = operator.id
                    sp.sign_time = datetime.now(timezone.utc)
                else:
                    sp.audit_status = "待签署"

        elif to_status == "待补充备案材料":
            sp.audit_status = "待编制"

        elif to_status == "审批通过":
            sp.audit_status = "已审核"

    async def reject(
        self, activity_id: UUID, operator: User, reason: str,
    ) -> ActivityStatusLog:
        activity = await self.db.get(Activity, activity_id)
        if activity is None:
            raise LookupError("活动不存在")

        if activity.status == "待安保方案设计":
            result = await self.transition(activity_id, "待安保方案设计", operator, reason)
        elif activity.status == "审批通过":
            result = await self.transition(activity_id, "待安保方案设计", operator, reason)
            for role_name in REJECT_NOTIFY_ROLES:
                await self.notification.notify_role(role_name, f"活动被驳回需重做: {reason}",
                    reference_id=activity_id, reference_type="activity")
        else:
            raise ValueError(f"当前状态 {activity.status} 不支持驳回操作")
        return result

    async def force_cancel(
        self, activity_id: UUID, operator: User, reason: str,
    ) -> ActivityStatusLog:
        return await self._force_terminal(activity_id, "已取消", operator, reason)

    async def force_postpone(
        self, activity_id: UUID, operator: User, reason: str,
    ) -> ActivityStatusLog:
        return await self._force_terminal(activity_id, "已延期", operator, reason)

    async def _force_terminal(
        self, activity_id: UUID, target: str, operator: User, reason: str,
    ) -> ActivityStatusLog:
        activity = await self.db.get(Activity, activity_id)
        if activity is None:
            raise LookupError("活动不存在")

        if activity.status in TERMINAL_STATUSES:
            raise ValueError("活动已处于终态")

        from_status = activity.status
        activity.status = target
        self.db.add(activity)

        log = ActivityStatusLog(
            activity_id=activity.id,
            from_status=from_status,
            to_status=target,
            operator_id=operator.id,
            comment=reason,
        )
        self.db.add(log)

        from app.models.activity import ImplementationRecord
        record = ImplementationRecord(
            activity_id=activity.id,
            admin_id=operator.id,
            change_status=target,
            change_reason=reason,
            archived_at=datetime.now(timezone.utc),
        )
        self.db.add(record)

        await self.db.commit()
        await self.db.refresh(log)

        await self.notification.notify_role("AdminStaff", f"活动 {activity.name} 已变更为 {target}: {reason}",
            reference_id=activity_id, reference_type="activity")
        return log
