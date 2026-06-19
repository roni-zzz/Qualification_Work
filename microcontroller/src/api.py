import urequests
import config


def send_status(url, payload):
    headers = {
        "Content-Type": "application/json",
        "X-ESP32-Secret": getattr(config, "ESP32_INGEST_SECRET", ""),
    }
    r = urequests.post(url, json=payload, headers=headers, timeout=10)
    try:
        print("Response Status:", r.status_code)
        print("Response Text:", r.text)
        code = r.status_code
        if code < 200 or code >= 300:
            raise OSError("HTTP %s" % code)
    finally:
        r.close()