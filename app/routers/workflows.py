from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.rbac import get_user_permissions, require_permission
from app.schemas.activity import StatusLogEntry
from app.schemas.workflow import ForceChangeRequest, RejectRequest, StatusTransition
from app.services.notification_service import NotificationService
from app.services.workflow_service import WorkflowService
from app.errors import NotFoundError, ValidationError

router = APIRouter(prefix="/activities", tags=["workflow"])


def _service(db=Depends(get_db)) -> WorkflowService:
    return WorkflowService(db, NotificationService(db))


@router.put("/{activity_id}/status", response_model=StatusLogEntry)
async def update_status(
    activity_id: UUID,
    body: StatusTransition,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
    svc: WorkflowService = Depends(_service),
):
    perms = await get_user_permissions(user=current_user, db=db)
    if "manage_security" not in perms and "audit_material" not in perms and "submit_plan" not in perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="缺少工作流操作权限"
        )
    if body.to_status == "审批通过-待举办" and "confirm_approval" not in perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="缺少权限: confirm_approval"
        )
    try:
        return await svc.transition(activity_id, body.to_status, current_user, body.comment)
    except LookupError as e:
        raise NotFoundError(str(e))
    except ValueError as e:
        raise ValidationError(str(e))


@router.post("/{activity_id}/reject", response_model=StatusLogEntry)
async def reject_activity(
    activity_id: UUID,
    body: RejectRequest,
    current_user: User = Depends(get_current_user),
    svc: WorkflowService = Depends(_service),
    _perm: None = require_permission("reject_approval"),
):
    try:
        return await svc.reject(activity_id, current_user, body.reason)
    except LookupError as e:
        raise NotFoundError(str(e))
    except ValueError as e:
        raise ValidationError(str(e))


@router.post("/{activity_id}/force-cancel", response_model=StatusLogEntry)
async def force_cancel(
    activity_id: UUID,
    body: ForceChangeRequest,
    current_user: User = Depends(get_current_user),
    svc: WorkflowService = Depends(_service),
    _perm: None = require_permission("force_cancel"),
):
    try:
        return await svc.force_cancel(activity_id, current_user, body.reason)
    except LookupError as e:
        raise NotFoundError(str(e))
    except ValueError as e:
        raise ValidationError(str(e))


@router.post("/{activity_id}/force-postpone", response_model=StatusLogEntry)
async def force_postpone(
    activity_id: UUID,
    body: ForceChangeRequest,
    current_user: User = Depends(get_current_user),
    svc: WorkflowService = Depends(_service),
    _perm: None = require_permission("force_postpone"),
):
    try:
        return await svc.force_postpone(activity_id, current_user, body.reason)
    except LookupError as e:
        raise NotFoundError(str(e))
    except ValueError as e:
        raise ValidationError(str(e))
