from typing import Dict, Set, Optional, List, Any
from pathlib import Path
from datetime import datetime

from app.config import settings

# In-memory cache
fcm_tokens_by_system: Dict[int, Set[str]] = {}
_firebase_initialized = False


# -----------------------------
# TOKEN REGISTRATION
# -----------------------------
def register_fcm_token(
    alarm_system_id: Optional[int],
    token: str,
    user_id: Optional[int] = None,
) -> tuple[bool, Optional[int]]:

    resolved_alarm_system_id = alarm_system_id

    # Always try resolve from user
    if resolved_alarm_system_id is None and user_id is not None:
        try:
            from db.connectToAlarmSystem import get_alarm_system_id_by_user_id
            resolved_alarm_system_id = get_alarm_system_id_by_user_id(user_id)
            print(f"[FCM REGISTER] user_id={user_id} resolved_alarm_system_id={resolved_alarm_system_id}")
        except Exception:
            resolved_alarm_system_id = None

    print(
        f"[FCM REGISTER] user_id={user_id}, "
        f"alarm_system_id={alarm_system_id}, "
        f"resolved={resolved_alarm_system_id}"
    )

    # ALWAYS store globally (important fallback)
    fcm_tokens_by_system.setdefault(-1, set()).add(token)

    # Store in system bucket if available
    if resolved_alarm_system_id is not None:
        fcm_tokens_by_system.setdefault(resolved_alarm_system_id, set()).add(token)

    # Persist in DB
    try:
        from db.fcm_tokens import save_fcm_token

        ok = save_fcm_token(resolved_alarm_system_id, token, user_id)

        if not ok:
            print("[FCM REGISTER] DB save failed")
            return False, resolved_alarm_system_id

        return True, resolved_alarm_system_id

    except Exception as e:
        print(f"[FCM REGISTER] exception: {e}")
        return False, resolved_alarm_system_id


# -----------------------------
# TOKEN RETRIEVAL
# -----------------------------
def _get_tokens_for_system(alarm_system_id: int) -> List[str]:
    try:
        from db.fcm_tokens import get_fcm_tokens, get_fcm_tokens_by_user_warehouse_link

        direct = get_fcm_tokens(alarm_system_id) or []
        linked = get_fcm_tokens_by_user_warehouse_link(alarm_system_id) or []

        tokens = list(set(direct + linked))
        print(f"[FCM DEBUG] system={alarm_system_id} tokens_found={len(tokens)}")
        return tokens

    except Exception as e:
        print(f"[FCM ERROR] token fetch failed: {e}")
        return []


def _debug_token_sources(alarm_system_id: int) -> None:
    """Print per-source token counts to diagnose registration/mapping issues quickly."""
    try:
        in_mem = list(fcm_tokens_by_system.get(alarm_system_id) or [])
        global_mem = list(fcm_tokens_by_system.get(-1) or [])
        direct_db = []
        linked_db = []
        try:
            from db.fcm_tokens import get_fcm_tokens, get_fcm_tokens_by_user_warehouse_link

            direct_db = get_fcm_tokens(alarm_system_id)
            linked_db = get_fcm_tokens_by_user_warehouse_link(alarm_system_id)
        except Exception as e:
            print(f"[FCM DEBUG] db source query failed for system={alarm_system_id}: {e}")

        print(
            "[FCM DEBUG] "
            f"system={alarm_system_id} "
            f"in_mem={len(set(in_mem))} "
            f"global_mem={len(set(global_mem))} "
            f"db_direct={len(set(direct_db))} "
            f"db_linked={len(set(linked_db))}"
        )
    except Exception as e:
        print(f"[FCM DEBUG] source diagnostic failed for system={alarm_system_id}: {e}")


def get_token_source_counts(alarm_system_id: int) -> Dict[str, int]:
    """Return token counts per source for API-level diagnostics."""
    in_mem = len(set(fcm_tokens_by_system.get(alarm_system_id) or []))
    global_mem = len(set(fcm_tokens_by_system.get(-1) or []))
    db_direct = 0
    db_linked = 0
    try:
        from db.fcm_tokens import get_fcm_tokens, get_fcm_tokens_by_user_warehouse_link

        db_direct = len(set(get_fcm_tokens(alarm_system_id)))
        db_linked = len(set(get_fcm_tokens_by_user_warehouse_link(alarm_system_id)))
    except Exception:
        pass
    return {
        "in_mem": in_mem,
        "global_mem": global_mem,
        "db_direct": db_direct,
        "db_linked": db_linked,
    }


# -----------------------------
# FIREBASE INIT
# -----------------------------
def init_firebase_if_needed() -> bool:
    global _firebase_initialized

    if _firebase_initialized:
        return True

    if not settings.firebase_credentials_path:
        print("Firebase disabled: missing credentials path")
        return False

    path = Path(settings.firebase_credentials_path)

    if not path.exists():
        print(f"Firebase credentials not found: {path}")
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            cred = credentials.Certificate(str(path))
            firebase_admin.initialize_app(cred)

        _firebase_initialized = True
        print("[FCM] Firebase initialized")
        return True

    except Exception as e:
        print(f"[FCM] init failed: {e}")
        return False


# -----------------------------
# MAIN SEND FUNCTION
# -----------------------------
def send_notification_to_system(
    alarm_system_id: int,
    title: str,
    body: str,
) -> int:

    tokens = _get_tokens_for_system(alarm_system_id)

    if not tokens:
        _debug_token_sources(alarm_system_id)
        print(
            f"[FCM SEND] NO TOKENS for system={alarm_system_id} "
            f"(check token registration / user mapping)"
        )
        return 0

    if not init_firebase_if_needed():
        print("[FCM SEND] Firebase not initialized")
        return 0

    try:
        from firebase_admin import messaging

        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            tokens=tokens,
        )

        batch = messaging.send_each_for_multicast(message)

        if batch.failure_count > 0:
            bad_tokens: List[str] = []
            for i, resp in enumerate(batch.responses):
                if resp.success:
                    continue
                err_obj = resp.exception
                err_text = str(err_obj) if err_obj is not None else "unknown"
                token_preview = tokens[i][-10:] if i < len(tokens) and tokens[i] else ""
                print(
                    f"[FCM SEND] failure[{i}] token=...{token_preview} error={err_text}"
                )
                if _should_prune_token_error(err_text):
                    bad_tokens.append(tokens[i])

            if bad_tokens:
                _prune_invalid_tokens(bad_tokens)

        print(
            f"[FCM SEND] system={alarm_system_id} "
            f"success={batch.success_count} "
            f"total={len(tokens)}"
        )

        return batch.success_count

    except Exception as e:
        print(f"[FCM SEND] error: {e}")
        return 0


def _should_prune_token_error(error_text: str) -> bool:
    t = (error_text or "").lower()
    return (
        "registration token is not a valid" in t
        or "requested entity was not found" in t
        or "not registered" in t
        or "invalid argument" in t
        or "mismatchsenderid" in t
    )


def _prune_invalid_tokens(tokens: List[str]) -> None:
    if not tokens:
        return
    try:
        from db.fcm_tokens import delete_fcm_token

        for token in set(tokens):
            ok = delete_fcm_token(token)
            print(
                f"[FCM SEND] prune token ...{token[-10:]} {'ok' if ok else 'failed'}"
            )
    except Exception as e:
        print(f"[FCM SEND] prune failed: {e}")

# Event types we send push for (ESP32 may send "led_toggle" for reed; backend also supports door_open/door_closed)
_PUSH_EVENT_TYPES = ("door_open", "door_closed", "door_open_2", "door_closed_2", "led_toggle")


def _format_event_time(timestamp: float) -> str:
    """Format Unix timestamp as e.g. 'Feb 18, 14:32'."""
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%b %d, %H:%M")
    except Exception:
        return ""


def _title_for_sensor_event(event_type: str, alarm_system_id: int) -> str:
    """Notification title aligned with admin-configured names (see db.sensor_labels)."""
    try:
        from db.sensor_labels import get_sensor_labels

        labels = get_sensor_labels(alarm_system_id)
    except Exception:
        labels = []
    n1 = (labels[0] if len(labels) > 0 else "").strip() or None
    n2 = (labels[1] if len(labels) > 1 else "").strip() or None

    if event_type == "door_open":
        return f"{n1} opened" if n1 else "Door opened"
    if event_type == "door_closed":
        return f"{n1} closed" if n1 else "Door closed"
    if event_type == "door_open_2":
        return f"{n2} opened" if n2 else "Sensor 2 opened"
    if event_type == "door_closed_2":
        return f"{n2} closed" if n2 else "Sensor 2 closed"
    return "Sensor event"


def send_push_for_event(event_dict: Dict[str, Any], alarm_system_id: Optional[int]):
    """event_dict must have event_type, device_id, timestamp (Unix float)."""
    event_type = event_dict.get("event_type")
    if event_type not in _PUSH_EVENT_TYPES:
        return

    if alarm_system_id is None:
        print(f"Push skipped: event {event_type} from {event_dict.get('device_id')} has no alarm_system_id (link ESP32 in app Settings)")
        return

    try:
        from db.fcm_tokens import get_fcm_tokens_excluding_contractor

        tokens = get_fcm_tokens_excluding_contractor(alarm_system_id)
    except Exception:
        tokens = _get_tokens_for_system(alarm_system_id)
    if not tokens:
        print(f"Push skipped: no FCM tokens for alarm_system_id={alarm_system_id} (open app while logged in to register)")
        return

    if not init_firebase_if_needed():
        print("Push skipped: Firebase not initialized (set FIREBASE_CREDENTIALS_PATH in backend .env)")
        return

    try:
        from firebase_admin import messaging

        if event_type in ("door_open", "door_closed", "door_open_2", "door_closed_2"):
            title = _title_for_sensor_event(event_type, alarm_system_id)
        else:
            title = "Sensor event"  # led_toggle or other
        ts = event_dict.get("timestamp")
        time_str = _format_event_time(ts) if isinstance(ts, (int, float)) else ""
        body = time_str or event_dict.get("device_id", "")
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data={"event_type": str(event_type), "device_id": event_dict.get("device_id", "")},
            tokens=tokens,
        )
        batch = messaging.send_each_for_multicast(message)
        print(f"Push sent: {event_type} to {batch.success_count}/{len(tokens)} devices (excludes contractor; failures: {batch.failure_count})")
        if batch.failure_count > 0:
            for i, err in enumerate(batch.responses):
                if not err.success:
                    print(f"  FCM failure[{i}]: {err.exception}")
    except Exception as e:
        print(f"FCM send failed: {e}")


def send_push_to_tokens(
    tokens: List[str],
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None,
) -> int:
    """Send FCM to an explicit token list. Returns success count."""
    if not tokens:
        return 0
    if not init_firebase_if_needed():
        return 0
    try:
        from firebase_admin import messaging

        android_config = messaging.AndroidConfig(
            notification=messaging.AndroidNotification(channel_id="sensor_events"),
            priority="high",
        )
        payload_data = {k: str(v) for k, v in (data or {}).items()}
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=payload_data,
            tokens=tokens,
            android=android_config,
        )
        batch = messaging.send_each_for_multicast(message)
        return batch.success_count
    except Exception as e:
        print(f"send_push_to_tokens failed: {e}")
        return 0


def notify_supervisors_worker_or_contractor_arm_action(
    alarm_system_id: int,
    actor_user_id: int,
    armed: bool,
) -> None:
    """Notify manager + supervisor when worker/contractor arms or disarms (immediate disarm path for worker only)."""
    try:
        from db.fcm_tokens import get_fcm_tokens_for_users
        from db.warehouse_roles import get_username, user_ids_guardians

        supervisors = [u for u in user_ids_guardians(alarm_system_id) if u != actor_user_id]
        if not supervisors:
            return
        name = get_username(actor_user_id)
        action = "armed" if armed else "disarmed"
        title = f"Alarm {action}"
        body = f"{name} {action} the alarm"
        tokens = get_fcm_tokens_for_users(alarm_system_id, supervisors)
        if not tokens:
            return
        send_push_to_tokens(tokens, title, body)
    except Exception as e:
        print(f"notify_supervisors_arm_action failed: {e}")


def notify_admins_disarm_approval_needed(
    alarm_system_id: int,
    request_id: str,
    actor_user_id: int,
) -> None:
    """
    Notify admins when a contractor requests disarm approval.
    """

    try:
        from db.fcm_tokens import get_fcm_tokens_for_users
        from db.warehouse_roles import get_username, user_ids_admins_only

        admins = user_ids_admins_only(alarm_system_id)

        if not admins:
            print(f"[FCM ADMIN] no admins for system={alarm_system_id}")
            return

        name = get_username(actor_user_id)

        title = "Approve disarm?"
        body = f"{name} requested to disarm the alarm. Open the app to approve or deny."

        tokens = get_fcm_tokens_for_users(alarm_system_id, admins)

        if not tokens:
            print(f"[FCM ADMIN] no tokens for system={alarm_system_id}")
            return

        send_push_to_tokens(
            tokens,
            title,
            body,
            data={
                "type": "disarm_request",
                "request_id": request_id,
            },
        )

    except Exception as e:
        print(f"[FCM ADMIN] error: {e}")


