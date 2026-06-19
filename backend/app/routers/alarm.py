import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from app.config import settings
from app.services.event_service import get_alarm_system_id_for_user, EVENTS, connected_clients
from db.events import save_event
from db.warehouse_roles import get_warehouse_role
from db.pending_disarm import create_pending, get_pending, list_pending_for_warehouse, set_status
from app.services.notification_service import (
    notify_supervisors_worker_or_contractor_arm_action,
    notify_admins_disarm_approval_needed,
)

router = APIRouter(prefix="/api/alarm", tags=["alarm"])
security = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> int:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing authorization")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=["HS256"],
        )
        user_id = payload.get("userId")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return int(user_id)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def _resolve_device_id_for_alarm_system(alarm_system_id: int) -> str:
    """Prefer a real microcontroller-based device id (esp32_<id>) for synthetic alarm events."""
    try:
        from db import connectToDB

        conn = connectToDB.connectToDB()
        if conn is None:
            return f"system_{alarm_system_id}"
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT microcontroller_id
                FROM microcontroller
                WHERE alarm_system_id = %s
                ORDER BY microcontroller_id
                LIMIT 1
                """,
                (alarm_system_id,),
            )
            row = cur.fetchone()
            if row and row[0] is not None:
                return f"esp32_{int(row[0])}"
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception:
        pass
    return f"system_{alarm_system_id}"


def _record_alarm_state_event(alarm_system_id: int, armed: bool) -> None:
    event_type = "alarm_enabled" if armed else "alarm_disabled"
    event_dict = {
        "device_id": _resolve_device_id_for_alarm_system(alarm_system_id),
        "event_type": event_type,
        "count": 1,
        "timestamp": time.time(),
    }
    EVENTS.append((event_dict, alarm_system_id, True))
    for queue, client_system_id in connected_clients:
        if client_system_id == alarm_system_id:
            queue.put_nowait(event_dict)
    try:
        save_event(event_dict, alarm_system_id, True)
    except Exception as persist_err:
        print(f"Alarm state event persist failed: {persist_err}")


def _apply_armed_state(alarm_system_id: int, armed: bool) -> None:
    from db.setModeAlarmSystem import setMode

    setMode(alarm_system_id, armed)
    _record_alarm_state_event(alarm_system_id, armed)


@router.get("", response_model=dict)
def get_armed_status(user_id: int = Depends(get_current_user_id)):
    """Return current armed state for the logged-in user's alarm system."""
    alarm_system_id = get_alarm_system_id_for_user(user_id)
    if alarm_system_id is None:
        raise HTTPException(status_code=400, detail="No alarm system linked")
    try:
        from db.getModeOfSystem import getModeBySysId

        armed = getModeBySysId(alarm_system_id)
        return {"armed": bool(armed) if armed is not None else False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("", response_model=dict)
def set_armed_status(
    body: dict,
    user_id: int = Depends(get_current_user_id),
):
    """Set armed state. Trusted users requesting disarm may receive pending_disarm instead."""
    alarm_system_id = get_alarm_system_id_for_user(user_id)
    if alarm_system_id is None:
        raise HTTPException(status_code=400, detail="No alarm system linked")
    armed = body.get("armed")
    if not isinstance(armed, bool):
        raise HTTPException(
            status_code=400,
            detail='Body must be { "armed": true } or { "armed": false }',
        )

    hr = get_warehouse_role(user_id) or "admin"

    # Contractor: disarm requires admin approval (stay armed until approved)
    if hr == "contractor" and armed is False:
        rid = str(uuid.uuid4())
        if not create_pending(alarm_system_id, user_id, rid):
            raise HTTPException(status_code=500, detail="Could not create disarm request")
        notify_admins_disarm_approval_needed(alarm_system_id, rid, user_id)
        return {"armed": True, "pending_disarm": True, "request_id": rid}

    # Worker / contractor arming, or worker disarming: apply immediately + notify guardians
    if hr in ("worker", "contractor") and armed is True:
        try:
            _apply_armed_state(alarm_system_id, True)
            notify_supervisors_worker_or_contractor_arm_action(alarm_system_id, user_id, True)
            return {"armed": True, "pending_disarm": False}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    if hr == "worker" and armed is False:
        try:
            _apply_armed_state(alarm_system_id, False)
            notify_supervisors_worker_or_contractor_arm_action(alarm_system_id, user_id, False)
            return {"armed": False, "pending_disarm": False}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Manager, supervisor, platform user defaults
    try:
        _apply_armed_state(alarm_system_id, armed)
        return {"armed": armed, "pending_disarm": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending-disarm-requests")
def list_my_pending_disarm_requests(user_id: int = Depends(get_current_user_id)):
    """List pending trusted disarm requests (admins only)."""
    alarm_system_id = get_alarm_system_id_for_user(user_id)
    if alarm_system_id is None:
        raise HTTPException(status_code=400, detail="No alarm system linked")
    if (get_warehouse_role(user_id) or "") != "admin":
        raise HTTPException(status_code=403, detail="Only the admin can view pending requests")
    return list_pending_for_warehouse(alarm_system_id)


@router.post("/disarm-requests/{request_id}/approve")
def approve_trusted_disarm(request_id: str, user_id: int = Depends(get_current_user_id)):
    alarm_system_id = get_alarm_system_id_for_user(user_id)
    if alarm_system_id is None:
        raise HTTPException(status_code=400, detail="No alarm system linked")
    if (get_warehouse_role(user_id) or "") != "admin":
        raise HTTPException(status_code=403, detail="Only the admin can approve")

    pending = get_pending(request_id)
    if not pending or pending["status"] != "pending":
        raise HTTPException(status_code=404, detail="Request not found or already handled")
    if int(pending["alarm_system_id"]) != int(alarm_system_id):
        raise HTTPException(status_code=403, detail="Not your warehouse")

    try:
        _apply_armed_state(alarm_system_id, False)
        set_status(request_id, "approved")
        return {"armed": False, "status": "approved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disarm-requests/{request_id}/deny")
def deny_trusted_disarm(request_id: str, user_id: int = Depends(get_current_user_id)):
    alarm_system_id = get_alarm_system_id_for_user(user_id)
    if alarm_system_id is None:
        raise HTTPException(status_code=400, detail="No alarm system linked")
    if (get_warehouse_role(user_id) or "") != "admin":
        raise HTTPException(status_code=403, detail="Only the admin can deny")

    pending = get_pending(request_id)
    if not pending or pending["status"] != "pending":
        raise HTTPException(status_code=404, detail="Request not found or already handled")
    if int(pending["alarm_system_id"]) != int(alarm_system_id):
        raise HTTPException(status_code=403, detail="Not your warehouse")

    set_status(request_id, "denied")
    return {"armed": True, "status": "denied"}
