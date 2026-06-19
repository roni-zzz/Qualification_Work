from typing import Annotated, Optional
from fastapi import Depends, HTTPException, Path, status
import jwt

from app.config import settings
from app.dependencies import get_current_user       # re-use existing JWT decode
from db import connectToDB
from db.connectToAlarmSystem import get_alarm_system_id_by_user_id

# Role constants 
ROLE_ADMIN       = "admin"
ROLE_SUPERVISOR  = "supervisor"
ROLE_CONTRACTOR  = "contractor"
ROLE_OTHER       = "other"
ROLE_USER        = "user"  

# Role types
_SENSOR_ROLES   = {ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_USER}
_ARM_ROLES      = {ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_CONTRACTOR, ROLE_OTHER, ROLE_USER}
_DISARM_ROLES   = {ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_CONTRACTOR, ROLE_USER}
_NOTIFY_ROLES   = {ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_USER}
_MODE_ROLES     = {ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_USER}


# Internal helpers
def _get_user_alarm_system_id(user_id: int) -> Optional[int]:
    return get_alarm_system_id_by_user_id(user_id)


def _get_user_role_from_db(user_id: int) -> str:
    conn = connectToDB.connectToDB()
    try:
        cur = conn.cursor()
        try:
            cur.execute("SELECT role FROM user_table WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return (row[0] or ROLE_USER) if row else ROLE_USER
        except Exception:
            conn.rollback()
            return ROLE_USER
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _resolve_user_context(
    jwt_payload: dict,
    requested_alarm_system_id: Optional[int] = None,
) -> dict:
    user_id: int = jwt_payload.get("userId") or jwt_payload.get("user_id")
    email: str   = jwt_payload.get("email", "")
    role: str    = jwt_payload.get("role", ROLE_USER)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing user identity",
        )

    db_role = _get_user_role_from_db(user_id)
    if db_role != role:
        role = db_role

    user_alarm_system_id = _get_user_alarm_system_id(user_id)

    # For non-admins, verify the path's alarm_system_id matches their own
    if requested_alarm_system_id is not None and role != ROLE_ADMIN:
        if user_alarm_system_id != requested_alarm_system_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this alarm system",
            )

    return {
        "user_id": user_id,
        "email": email,
        "role": role,
        "alarm_system_id": user_alarm_system_id,
    }


def _require_role_for_system(
    jwt_payload: dict,
    alarm_system_id: int,
    allowed_roles: set,
    action_description: str,
) -> dict:
    user = _resolve_user_context(jwt_payload, alarm_system_id)
    if user["role"] not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your role '{user['role']}' does not have permission to: {action_description}",
        )
    return user



def require_sensor_access(
    alarm_system_id: Annotated[int, Path()],
    jwt_payload: Annotated[dict, Depends(get_current_user)],
) -> dict:
    return _require_role_for_system(
        jwt_payload,
        alarm_system_id,
        _SENSOR_ROLES,
        "view sensor data",
    )


def require_mode_access(
    alarm_system_id: Annotated[int, Path()],
    jwt_payload: Annotated[dict, Depends(get_current_user)],
) -> dict:
    return _require_role_for_system(
        jwt_payload,
        alarm_system_id,
        _MODE_ROLES,
        "view system armed/disarmed mode",
    )


def require_arm_permission(
    alarm_system_id: Annotated[int, Path()],
    jwt_payload: Annotated[dict, Depends(get_current_user)],
) -> dict:
    return _require_role_for_system(
        jwt_payload,
        alarm_system_id,
        _ARM_ROLES,
        "arm the alarm system",
    )


def require_disarm_permission(
    alarm_system_id: Annotated[int, Path()],
    jwt_payload: Annotated[dict, Depends(get_current_user)],
) -> dict:
    return _require_role_for_system(
        jwt_payload,
        alarm_system_id,
        _DISARM_ROLES,
        "disarm the alarm system",
    )


def require_notification_permission(
    alarm_system_id: Annotated[int, Path()],
    jwt_payload: Annotated[dict, Depends(get_current_user)],
) -> dict:
    return _require_role_for_system(
        jwt_payload,
        alarm_system_id,
        _NOTIFY_ROLES,
        "manage push notifications",
    )


def require_system_admin(
    alarm_system_id: Annotated[int, Path()],
    jwt_payload: Annotated[dict, Depends(get_current_user)],
) -> dict:
    return _require_role_for_system(
        jwt_payload,
        alarm_system_id,
        _SENSOR_ROLES,   # same set as sensor access — admin-level actions
        "manage this alarm system",
    )



def get_authenticated_system_user(
    alarm_system_id: Annotated[int, Path()],
    jwt_payload: Annotated[dict, Depends(get_current_user)],
) -> dict:
    return _resolve_user_context(jwt_payload, alarm_system_id)