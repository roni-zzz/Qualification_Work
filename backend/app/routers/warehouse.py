"""Manager-only: manage members of their warehouse (not platform admin)."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from app.security import AuthenticatedUser, get_current_user
from app.models.request_models import NotifyManagerRequest
from app.services.event_service import get_alarm_system_id_for_user
from app.services.notification_service import (
    send_notification_to_system,
    register_fcm_token,
    get_token_source_counts,
)
from db import admin_queries
from db.warehouse_roles import get_warehouse_role
from db.insertIntoDB import unlink_user_from_warehouse, update_user_by_admin

router = APIRouter(prefix="/api/warehouse", tags=["warehouse"])


class PatchMemberBody(BaseModel):
    warehouse_role: str = Field(..., min_length=3, max_length=20)


@router.get("/members")
def list_warehouse_members(current_user: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    alarm_system_id = get_alarm_system_id_for_user(current_user.user_id)
    if alarm_system_id is None:
        return []
    if (get_warehouse_role(current_user.user_id) or "") != "admin":
        raise HTTPException(status_code=403, detail="Only the admin can manage members")
    return admin_queries.list_users_for_warehouse(alarm_system_id)


@router.patch("/members/{member_id}")
def patch_warehouse_member(
    member_id: int,
    body: PatchMemberBody,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
):
    alarm_system_id = get_alarm_system_id_for_user(current_user.user_id)
    if alarm_system_id is None:
        raise HTTPException(status_code=400, detail="No alarm system linked")
    if (get_warehouse_role(current_user.user_id) or "") != "admin":
        raise HTTPException(status_code=403, detail="Only the admin can change roles")
    if member_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="You cannot change your own role here")

    ok = update_user_by_admin(
        member_id,
        alarm_system_id,
        warehouse_role=body.warehouse_role,
    )
    if not ok:
        raise HTTPException(
            status_code=400,
            detail="Update failed (invalid role, or another admin already exists)",
        )
    return {"status": "ok"}


@router.delete("/members/{member_id}")
def remove_warehouse_member(
    member_id: int,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
):
    alarm_system_id = get_alarm_system_id_for_user(current_user.user_id)
    if alarm_system_id is None:
        raise HTTPException(status_code=400, detail="No alarm system linked")
    if (get_warehouse_role(current_user.user_id) or "") != "admin":
        raise HTTPException(status_code=403, detail="Only the admin can remove members")
    if member_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="You cannot remove yourself")

    if not unlink_user_from_warehouse(member_id, alarm_system_id):
        raise HTTPException(status_code=404, detail="User not found in this warehouse")
    return {"status": "ok"}


@router.post("/notify")
def notify_warehouse_users(
    body: NotifyManagerRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    x_fcm_token: str | None = Header(default=None),
):
    """Allow any linked warehouse user to send a one-off notification to devices in their warehouse."""
    alarm_system_id = get_alarm_system_id_for_user(current_user.user_id)
    if alarm_system_id is None:
        raise HTTPException(status_code=400, detail="No alarm system linked")

    print(
        f"[FCM INLINE REGISTER][warehouse notify] user_id={current_user.user_id} alarm_system_id={alarm_system_id} "
        f"header_present={bool(x_fcm_token)} token_len={(len(x_fcm_token) if x_fcm_token else 0)}"
    )
    if x_fcm_token:
        ok, resolved = register_fcm_token(alarm_system_id, x_fcm_token, current_user.user_id)
        print(
            f"[FCM INLINE REGISTER][warehouse notify] user_id={current_user.user_id} alarm_system_id={alarm_system_id} ok={ok} resolved={resolved}"
        )

    sources_before_send = get_token_source_counts(alarm_system_id)
    if (not x_fcm_token) and sum(sources_before_send.values()) == 0:
        raise HTTPException(
            status_code=400,
            detail="No FCM token available. Open app, allow notifications, and sign in again to register token.",
        )

    count = send_notification_to_system(alarm_system_id, body.title, body.body)
    return {
        "sent_to_devices": count,
        "header_present": bool(x_fcm_token),
        "token_len": len(x_fcm_token) if x_fcm_token else 0,
        "token_sources": get_token_source_counts(alarm_system_id),
    }
