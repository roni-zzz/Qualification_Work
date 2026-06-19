import urequests
import config


def send_status(url, payload):
    try:
        headers = {
            "Content-Type": "application/json",
            "X-ESP32-Secret": getattr(config, "ESP32_INGEST_SECRET", ""),
        }
        r = urequests.post(url, json=payload, headers=headers, timeout=10)
        print("Response Status:", r.status_code)
        print("Response Text:", r.text)
        r.close()
    except Exception as e:
        raise e