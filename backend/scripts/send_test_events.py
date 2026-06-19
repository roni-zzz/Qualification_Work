"""
Send test sensor events to the backend (simulates ESP32).
Run with backend running: py run.py (from backend folder).

Usage (from repo root):
  py backend/scripts/send_test_events.py
  py backend/scripts/send_test_events.py --base http://127.0.0.1:8000

From backend folder:
  py scripts/send_test_events.py
"""
import argparse
import json
import time
import urllib.request
import urllib.error

EVENT_TYPES = ["door_open", "door_closed", "alarm_enabled", "alarm_disabled"]

DEFAULT_BASE = "http://127.0.0.1:5000"
# Match setup_two_test_accounts.py: account 1 -> 111, account 2 -> 222
DEVICE_ACCOUNT_1 = "esp32_111"
DEVICE_ACCOUNT_2 = "esp32_222"


def send_event(base_url: str, device_id: str, event_type: str, count: int) -> bool:
    url = f"{base_url.rstrip('/')}/api/events"
    payload = {
        "device_id": device_id,
        "event_type": event_type,
        "count": count,
        "timestamp": time.time(),
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.getcode() == 200
    except urllib.error.HTTPError as e:
        print(f"HTTP error {e.code}: {e.read().decode()}")
        return False
    except Exception as e:
        print(f"Request failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Send test events to the backend")
    parser.add_argument(
        "--base",
        default=DEFAULT_BASE,
        help=f"Backend base URL (default: {DEFAULT_BASE})",
    )
    parser.add_argument(
        "--device",
        default="esp32_001",
        help="Device ID (default: esp32_001)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Send one event and exit (default: send a few in sequence)",
    )
    parser.add_argument(
        "--both",
        action="store_true",
        help="Send one event to each test account (esp32_111 and esp32_222). Use after setup_two_test_accounts.py",
    )
    args = parser.parse_args()

    base = args.base.rstrip("/")
    device_id = args.device

    if args.both:
        ok1 = send_event(base, DEVICE_ACCOUNT_1, "door_open", 1)
        ok2 = send_event(base, DEVICE_ACCOUNT_2, "door_closed", 1)
        print(f"  {DEVICE_ACCOUNT_1} door_open -> {'ok' if ok1 else 'FAILED'}")
        print(f"  {DEVICE_ACCOUNT_2} door_closed -> {'ok' if ok2 else 'FAILED'}")
        print("Account 1 sees door_open; Account 2 sees door_closed.")
        return

    if args.once:
        ok = send_event(base, device_id, "door_open", 1)
        print("door_open sent" if ok else "Send failed")
        return

    # Send a short sequence so you see events appear on the app
    events = [
        ("door_open", 1),
        ("door_closed", 2),
        ("door_open", 3),
        ("door_closed", 4),
    ]
    for event_type, count in events:
        ok = send_event(base, device_id, event_type, count)
        status = "ok" if ok else "FAILED"
        print(f"  {event_type} (count={count}) -> {status}")
        if ok and event_type != events[-1][0]:
            time.sleep(1.5)
    print("Done. Check the app warehouse screen for events.")


if __name__ == "__main__":
    main()
