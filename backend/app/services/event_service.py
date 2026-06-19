import asyncio
import time
from typing import List, Tuple, Optional

from db.connectToAlarmSystem import (
    get_alarm_system_id_by_user_id,
    get_alarm_system_id_by_device_id,
)

# (event_dict, alarm_system_id, was_armed_when_received)
EVENTS: List[Tuple[dict, Optional[int], bool]] = []

# (queue, alarm_system_id)
connected_clients: List[Tuple[asyncio.Queue, Optional[int]]] = []

# --- Replay attack detection ---

_DEDUP_WINDOW = 180  # seconds

# Maps (device_id, count) -> timestamp of first receipt
_seen_events: dict = {}

# Maps device_id -> last accepted count
_last_counts: dict = {}


def is_duplicate(device_id: str, count: int) -> bool:
    """Return True if (device_id, count) was already seen within the dedup window."""
    now = time.time()
    cutoff = now - _DEDUP_WINDOW

    expired = [k for k, ts in _seen_events.items() if ts < cutoff]
    for k in expired:
        del _seen_events[k]

    key = (device_id, count)
    if key in _seen_events:
        return True

    _seen_events[key] = now
    return False


def is_sequence_valid(device_id: str, count: int) -> bool:
    """
    Per-device monotonic tracking. Gaps are allowed: firmware may increment count before a successful
    POST, so the server can see e.g. 5 then 7 while 6 never arrived.
    Resets (count <= last) handle ESP reboots while the server still holds a high water mark in RAM.
    """
    last = _last_counts.get(device_id)
    if last is None:
        _last_counts[device_id] = count
        return True
    if count <= last:
        _last_counts[device_id] = count
        return True
    # count > last — forward progress (including last+1 or gaps)
    _last_counts[device_id] = count
    return True


def get_alarm_system_id_for_user(user_id: int) -> Optional[int]:
    return get_alarm_system_id_by_user_id(user_id)


def get_alarm_system_id_for_device(device_id: str) -> Optional[int]:
    return get_alarm_system_id_by_device_id(device_id)
