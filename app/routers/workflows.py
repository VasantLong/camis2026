from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.rbac import require_permission
from app.schemas.activity import StatusLogEntry
from app.schemas.workflow import ForceChangeRequest, RejectRequest, StatusTransition
from app.services.notification_service import NotificationService
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/activities", tags=["workflow"])


def _service(db=Depends(get_db)) -> WorkflowService:
    return WorkflowService(db, NotificationService())


@router.put("/{activity_id}/status", response_model=StatusLogEntry)
async def update_status(
    activity_id: UUID,
    body: StatusTransition,
    current_user: User = Depends(get_current_user),
    svc: WorkflowService = Depends(_service),
    _perm: None = require_permission("manage_security"),
):
    try:
        return await svc.transition(activity_id, body.to_status, current_user, body.comment)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
