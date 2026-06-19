import network
import time

def connect(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print('Connecting to WiFi...')
        wlan.disconnect() # Clear any stuck connection attempts 
        wlan.connect(ssid, password)
        networks = wlan.scan() 
        timeout = 30
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            print('.')
    
    if wlan.isconnected():
        print('Connected! IP:', wlan.ifconfig()[0])
        return True
    else:
        print('Failed to connect to WiFi')
        return False

def create_ap(ssid, password):
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=ssid, password=password)
    
    while not ap.active():
        time.sleep(1)
    
    print('Access Point created!')
    print('SSID:', ssid)
    print('Password:', password)
    print('IP Address:', ap.ifconfig()[0])
    print('Connect your laptop to this network')
    return ap.ifconfig()[0]