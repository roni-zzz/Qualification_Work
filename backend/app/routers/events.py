#
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import json
import time
from typing import Optional

from app.config import settings
from app.validate2 import ValidateData, ValidateDataIngest
from app.security import get_current_user, AuthenticatedUser
from app.services.event_service import (
    EVENTS,
    connected_clients,
    get_alarm_system_id_for_user,
    get_alarm_system_id_for_device,
    is_duplicate,
    is_sequence_valid,
)
from db.events import save_event, get_events_for_system, get_power_samples_for_system
from db.warehouse_roles import can_view_history, get_warehouse_role
from db.sensor_labels import get_sensor_labels
from db.device_last_seen import update_last_seen
from app.services.notification_service import send_push_for_event

router = APIRouter()


def is_microcontroller_registered_to_user(device_id: str, user_id: int) -> bool:
    user_system_id = get_alarm_system_id_for_user(user_id)
    device_system_id = get_alarm_system_id_for_device(device_id)
    return user_system_id is not None and user_system_id == device_system_id


def _is_system_armed(alarm_system_id) -> bool:
    """True if this alarm system is armed (push/alert only when armed)."""
    if alarm_system_id is None:
        return False
    try:
        from db.getModeOfSystem import getModeBySysId
        return bool(getModeBySysId(alarm_system_id))
    except Exception:
        return False


def _apply_event(event: ValidateData, idempotent_duplicate: bool = False) -> dict:
    """Validate dedup/sequence, persist, stream, notify. Returns response dict."""
    if is_duplicate(event.device_id, event.count):
        if idempotent_duplicate:
            return {"status": "ok", "message": "Duplicate event ignored", "duplicate": True}
        raise HTTPException(status_code=409, detail="Duplicate event")

    is_sequence_valid(event.device_id, event.count)  # updates per-device high-water (gaps allowed)

    alarm_system_id = get_alarm_system_id_for_device(event.device_id)

    event_dict = event.model_dump()
    event_dict["timestamp"] = time.time()
    was_armed = _is_system_armed(alarm_system_id)
    EVENTS.append((event_dict, alarm_system_id, was_armed))

    try:
        save_event(event_dict, alarm_system_id, was_armed)
    except Exception as e:
        print(f"Event persist error: {e}")

    if alarm_system_id is not None:
        try:
            update_last_seen(event.device_id, event_dict["timestamp"])
        except Exception:
            pass
    if event.event_type == "current_power_usage":
        print(f"Power Event #{event.count} received. Usage: {event.value}mA")

    for queue, client_system_id in connected_clients:
        if client_system_id == alarm_system_id:
            queue.put_nowait(event_dict)

    if _is_system_armed(alarm_system_id):
        send_push_for_event(event_dict, alarm_system_id)

    return {"status": "ok", "message": "Event received"}


@router.post("/api/events")
def receive_event(
    event: ValidateData,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    if not is_microcontroller_registered_to_user(event.device_id, current_user.user_id):
        raise HTTPException(status_code=403, detail="Device not registered to this user")

    return _apply_event(event, idempotent_duplicate=False)


@router.post("/api/events/ingest")
def receive_event_device(
    body: ValidateDataIngest,
    x_esp32_secret: Optional[str] = Header(None, alias="X-ESP32-Secret"),
):
    """
    ESP32 / MicroPython: use this instead of POST /api/events (no user JWT on device).
    Set the same secret in backend .env (ESP32_INGEST_SECRET) and on the board.
    The microcontroller must already be linked to a warehouse (app: device connect / admin).
    Client timestamps are ignored (ESP32 often has no NTP); server time is used in validation.
    """
    secret = (settings.esp32_ingest_secret or "").strip()
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="ESP32 ingest disabled: set ESP32_INGEST_SECRET in backend .env",
        )
    if (x_esp32_secret or "").strip() != secret:
        raise HTTPException(status_code=401, detail="Invalid or missing X-ESP32-Secret")

    if get_alarm_system_id_for_device(body.device_id) is None:
        raise HTTPException(
            status_code=403,
            detail="Device not linked to a warehouse — connect it in the app (or admin) first",
        )

    event = ValidateData(
        device_id=body.device_id,
        event_type=body.event_type,
        count=body.count,
        value=body.value,
        timestamp=time.time(),
    )
    return _apply_event(event, idempotent_duplicate=True)


@router.get("/events")
def get_events(current_user: AuthenticatedUser = Depends(get_current_user)):
    alarm_system_id = get_alarm_system_id_for_user(current_user.user_id)

    # No linked warehouse/system means no history; avoid extra role lookup work.
    if alarm_system_id is None:
        return []

    hr = get_warehouse_role(current_user.user_id)
    if not can_view_history(hr):
        raise HTTPException(status_code=403, detail="Sensor history is not available for your role")

    events = get_events_for_system(
        alarm_system_id,
        armed_only=True,
        exclude_event_types=["current_power_usage"],
    )
    return events


@router.get("/api/sensor-labels")
def get_my_sensor_labels(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Display names for sensors (positions 0 = first reed, 1 = second) set by admin."""
    alarm_system_id = get_alarm_system_id_for_user(current_user.user_id)
    if alarm_system_id is None:
        return {"labels": []}
    return {"labels": get_sensor_labels(alarm_system_id)}


@router.get("/api/power/recent")
def get_recent_power(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Recent power readings (mA) for live energy view; not filtered by armed state."""
    alarm_system_id = get_alarm_system_id_for_user(current_user.user_id)
    if alarm_system_id is None:
        return []
    return get_power_samples_for_system(alarm_system_id, limit=120)


@router.get("/events/stream")
async def stream_events(current_user: AuthenticatedUser = Depends(get_current_user)):
    hr = get_warehouse_role(current_user.user_id)
    if not can_view_history(hr):
        raise HTTPException(status_code=403, detail="Sensor history is not available for your role")

    alarm_system_id = get_alarm_system_id_for_user(current_user.user_id)

    queue: asyncio.Queue = asyncio.Queue()
    entry = (queue, alarm_system_id)
    connected_clients.append(entry)

    async def event_generator():
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            if entry in connected_clients:
                connected_clients.remove(entry)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
