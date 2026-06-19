"""
Admin-only API: list/add warehouses, sensor labels, add users to warehouse, offline devices, notify admin.
No warehouse address is ever stored or returned.
"""
from typing import Annotated
from fastapi import APIRouter, Body, Depends, HTTPException, Header

from app.dependencies import get_current_admin
from app.models.request_models import (
    AddWarehouseRequest,
    SetSensorLabelsRequest,
    AddUserToWarehouseRequest,
    LinkExistingUserToWarehouseRequest,
    NotifyManagerRequest,
    UpdateAlarmSystemRequest,
    UpdateUserRequest,
)
from app.services.notification_service import (
    send_notification_to_system,
    register_fcm_token,
    get_token_source_counts,
)
from db import admin_queries
from db.device_last_seen import get_offline_devices
from db.sensor_labels import set_sensor_labels, get_sensor_labels
from db.insertIntoDB import (
    insert_user_by_admin,
    update_user_by_admin,
    unlink_user_from_warehouse,
    link_existing_user_to_warehouse,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/warehouses")
def list_warehouses(_: Annotated[dict, Depends(get_current_admin)]):
    """List all warehouses (alarm systems) with device_id, last_seen, offline flag, sensor labels, user count. No address."""
    return admin_queries.list_warehouses()


@router.post("/warehouses")
def add_warehouse(
    _: Annotated[dict, Depends(get_current_admin)],
    body: AddWarehouseRequest = Body(default_factory=AddWarehouseRequest),
):
    """
    Create a new warehouse (alarm_system + one microcontroller).
    Pass microcontroller_id to match an ESP already flashed with DEVICE_ID=esp32_<n> (same numeric n).
    Omit it to allocate the next free id.
    """
    try:
        result = admin_queries.add_warehouse(body.microcontroller_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to create warehouse")
    return result


@router.patch("/warehouses/{alarm_system_id}")
def update_warehouse(
    alarm_system_id: int,
    body: UpdateAlarmSystemRequest,
    _: Annotated[dict, Depends(get_current_admin)],
):
    """Update alarm system display name."""
    if not admin_queries.update_warehouse_name(alarm_system_id, body.name):
        raise HTTPException(status_code=404, detail="Alarm system not found")
    return {"status": "ok"}


@router.delete("/warehouses/{alarm_system_id}")
def delete_warehouse(
    alarm_system_id: int,
    _: Annotated[dict, Depends(get_current_admin)],
):
    """Delete alarm system; users are unlinked (not deleted)."""
    ok, err = admin_queries.delete_warehouse(alarm_system_id)
    if not ok:
        raise HTTPException(status_code=500, detail=err or "Failed to delete")
    return {"status": "ok"}


@router.get("/warehouses/{alarm_system_id}/sensors")
def get_sensors(
    alarm_system_id: int,
    _: Annotated[dict, Depends(get_current_admin)],
):
    """Get sensor labels for a warehouse."""
    return {"labels": get_sensor_labels(alarm_system_id)}


@router.put("/warehouses/{alarm_system_id}/sensors")
def update_sensors(
    alarm_system_id: int,
    body: SetSensorLabelsRequest,
    _: Annotated[dict, Depends(get_current_admin)],
):
    """Set display names for sensors (e.g. Front door, Back window)."""
    if not set_sensor_labels(alarm_system_id, body.labels):
        raise HTTPException(status_code=500, detail="Failed to update sensor labels")
    return {"labels": get_sensor_labels(alarm_system_id)}


@router.get("/warehouses/{alarm_system_id}/users")
def list_users_for_warehouse(
    alarm_system_id: int,
    _: Annotated[dict, Depends(get_current_admin)],
):
    """List users linked to this warehouse (id, username, email, phone). No address."""
    return admin_queries.list_users_for_warehouse(alarm_system_id)


@router.post("/warehouses/{alarm_system_id}/users")
def add_user_to_warehouse(
    alarm_system_id: int,
    body: AddUserToWarehouseRequest,
    _: Annotated[dict, Depends(get_current_admin)],
):
    """Create a admin user for this warehouse (they log in with email/password)."""
    if not insert_user_by_admin(
        username=body.username.strip(),
        email=body.email.strip().lower(),
        password=body.password,
        alarm_system_id=alarm_system_id,
        phone=body.phone.strip() if body.phone else None,
        warehouse_role=(body.warehouse_role.strip().lower() if body.warehouse_role else None),
    ):
        raise HTTPException(status_code=400, detail="User already exists or invalid data")
    return {"status": "ok", "message": "User created"}


@router.post("/warehouses/{alarm_system_id}/users/link")
def link_existing_user_to_warehouse_endpoint(
    alarm_system_id: int,
    body: LinkExistingUserToWarehouseRequest,
    _: Annotated[dict, Depends(get_current_admin)],
):
    """
    Link an existing account (same email already in user_table, e.g. Google sign-in) to this warehouse.
    Optionally set a password so they can use email/password login as well.
    """
    pwd = (body.password or "").strip()
    if pwd and len(pwd) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters if provided")
    err = link_existing_user_to_warehouse(
        email=body.email.strip(),
        alarm_system_id=alarm_system_id,
        password=pwd if pwd else None,
        warehouse_role=(body.warehouse_role.strip().lower() if body.warehouse_role else None),
    )
    if err == "admin_exists":
        raise HTTPException(
            status_code=409,
            detail="A admin already exists — choose supervisor, worker, or contractor",
        )
    if err == "not_found":
        raise HTTPException(status_code=404, detail="No user with that email — they must sign up or log in once first")
    if err == "already_other_warehouse":
        raise HTTPException(
            status_code=409,
            detail="That user is already assigned to a different warehouse — remove them there first",
        )
    if err:
        raise HTTPException(status_code=500, detail="Could not link user")
    return {"status": "ok", "message": "User linked to this warehouse"}


@router.put("/warehouses/{alarm_system_id}/users/{user_id}")
def update_user_in_warehouse(
    alarm_system_id: int,
    user_id: int,
    body: UpdateUserRequest,
    _: Annotated[dict, Depends(get_current_admin)],
):
    """Update a user in this warehouse (username, email, phone, or password)."""
    if not update_user_by_admin(
        user_id=user_id,
        alarm_system_id=alarm_system_id,
        username=body.username,
        email=body.email,
        phone=body.phone,
        password=body.password,
        warehouse_role=(body.warehouse_role.strip().lower() if body.warehouse_role else None),
    ):
        raise HTTPException(status_code=400, detail="User not found or invalid data")
    return {"status": "ok"}


@router.delete("/warehouses/{alarm_system_id}/users/{user_id}")
def remove_user_from_warehouse(
    alarm_system_id: int,
    user_id: int,
    _: Annotated[dict, Depends(get_current_admin)],
):
    """Remove user from this warehouse (unlink; does not delete account)."""
    if not unlink_user_from_warehouse(user_id, alarm_system_id):
        raise HTTPException(status_code=404, detail="User not found in this warehouse")
    return {"status": "ok"}


@router.get("/offline")
def list_offline(_: Annotated[dict, Depends(get_current_admin)]):
    """List devices that have not been seen in the last 5 minutes (microcontroller_id, alarm_system_id, last_seen)."""
    rows = get_offline_devices(300)
    return [
        {"microcontroller_id": r[0], "alarm_system_id": r[1], "last_seen": r[2]}
        for r in rows
    ]


@router.post("/warehouses/{alarm_system_id}/notify")
def notify_admin(
    alarm_system_id: int,
    body: NotifyManagerRequest,
    current_admin: Annotated[dict, Depends(get_current_admin)],
    x_fcm_token: str | None = Header(default=None),
):
    """Send a push notification to all devices registered for this warehouse (e.g. sensor offline alert)."""
    user_id = int(current_admin.get("userId")) if current_admin.get("userId") is not None else None
    print(
        f"[FCM INLINE REGISTER][admin notify] user_id={user_id} alarm_system_id={alarm_system_id} "
        f"header_present={bool(x_fcm_token)} token_len={(len(x_fcm_token) if x_fcm_token else 0)}"
    )
    if x_fcm_token:
        ok, resolved = register_fcm_token(alarm_system_id, x_fcm_token, user_id)
        print(
            f"[FCM INLINE REGISTER][admin notify] user_id={user_id} alarm_system_id={alarm_system_id} ok={ok} resolved={resolved}"
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
