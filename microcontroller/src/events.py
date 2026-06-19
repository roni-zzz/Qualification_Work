import time
import api
import config

class EventManager:
    def __init__(self, device_id="esp32_1"):
        self.device_id = device_id
        self.event_count = 0
        self.event_value = 0
        self.handlers = []
        self.failed_events = []  
    
    def send(self, event_type, **kwargs): # no execution, just send data
        # Assign count only after a successful POST so the server never sees gaps (e.g. 5 then 7).
        next_count = self.event_count + 1
        payload = {
            "event_type": event_type,
            "device_id": self.device_id,
            "count": next_count,
            "value": self.event_value,
            "timestamp": time.time()
        }
        # kwargs passes event data w/o defining specific event parameters
        payload.update(kwargs)

        try:
            api.send_status(config.BACKEND_URL, payload)
            self.event_count = next_count
            print("Event " + str(self.event_count) + " sent: " + event_type)
            return True
        except Exception as e:
            print("Failed to send event: " + str(e))
            self.failed_events.append(payload)
            return False
    
    def do(self, event_type, action, **kwargs): # execute function and send 
        result = action() if callable(action) else None
        
        if isinstance(result, dict):
            kwargs.update(result)
        
        return self.send(event_type, **kwargs)
    
    def on(self, event_type, trigger_func, handler_func=None): # auto check
        self.handlers.append({
            "event_type": event_type,
            "trigger": trigger_func,
            "handler": handler_func
        })
    
    def check_all(self): # check failed and on events
        # resend failed events 
        for payload in self.failed_events[:]:
            try:
                api.send_status(config.BACKEND_URL, payload)
                self.event_count = payload.get("count", self.event_count)
                self.failed_events.remove(payload)
                print("retry success: " + payload["event_type"])
            except Exception:
                pass  # keep in queue for next retry
        
        for h in self.handlers:
            result = h["trigger"]()
            print(result)
            if result:
                if h["handler"]:
                    h["handler"]()
                
                if isinstance(result, dict):
                    data = result
                else:
                    data = {"value": result}
                print(data)
                self.send(h["event_type"], **data)
        
