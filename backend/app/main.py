from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import socket

from app.config import settings
from app.routers import auth, events, users, pairing, notifications, alarm, admin, warehouse
from app.models.response_models import HealthResponse
from app.rate_limit import SlidingWindow, RateLimitMiddleware


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure DB has phone/role columns and admin tables (same DB the app uses)
    try:
        from db.ensure_schema import run_startup_migration
        run_startup_migration()
    except Exception as e:
        print(f"Startup migration (optional): {e}")

    local_ip = get_local_ip()
    port = settings.port
    effective_url = settings.backend_url or f"http://{local_ip}:{port}"

    print("============================================")
    print("Warehouse Alarm Backend started")
    print(f"Network URL: {effective_url}")
    print(f"Loopback:    http://127.0.0.1:{port}")
    print("============================================")

    yield

    print("Warehouse Alarm Backend shutting down")


app = FastAPI(
    title="Warehouse Alarm Backend",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

rate_limiter = SlidingWindow(max_requests=100, window_seconds=60)
app.add_middleware(RateLimitMiddleware, limiter=rate_limiter)

# Include routers
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(users.router)
app.include_router(pairing.router)
app.include_router(notifications.router)
app.include_router(alarm.router)
app.include_router(admin.router)
app.include_router(warehouse.router)


@app.get("/health", response_model=HealthResponse)
def health():
    return {
        "status": "ok",
        "service": "backend",
        "backend_url": settings.backend_url
    }
