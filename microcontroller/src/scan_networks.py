import network
import time

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

print("=== SCANNING AVAILABLE NETWORKS ===")
time.sleep(1)
networks = wlan.scan()

print(f"Found {len(networks)} networks:\n")
for n in networks:
    ssid = n[0].decode('utf-8', errors='ignore')
    bssid = ':'.join(f'{b:02x}' for b in n[1])
    channel = n[2]
    rssi = n[3]
    security = n[4]
    hidden = n[5]
    
    print(f"SSID: {ssid}")
    print(f"  Channel: {channel}")
    print(f"  Signal: {rssi} dBm")
    print(f"  Security: {security}")
    print(f"  Hidden: {hidden}")
    print()
