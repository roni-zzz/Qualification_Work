from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from app.config import settings
from app.security import get_current_user, AuthenticatedUser
from app.models.request_models import (
    PairUserRequest,
    ConnectMicrocontrollerRequest,
    ConnectDeviceRequest,
)
from app.models.response_models import SimpleStatusResponse, MicrocontrollerConnectResponse
from db.connectToAlarmSystem import (
    connectUserToSystem,
    get_alarm_system_id_by_user_id,
    get_username_by_user_id,
)
from db.connectMCtoAlarmSystem import connect_microcontroller_by_user_id

router = APIRouter()
security = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> int:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing authorization")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=["HS256"],
        )
        user_id = payload.get("userId")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return int(user_id)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.post("/api/pair", response_model=SimpleStatusResponse)
def pair_user(
    request: PairUserRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    if not connectUserToSystem(current_user.user_id, request.system_password):
        raise HTTPException(status_code=400, detail="Pairing failed")

    return {"status": "ok", "message": "Paired successfully"}


@router.post("/api/microcontroller/connect", response_model=MicrocontrollerConnectResponse)
def connect_microcontroller(
    request: ConnectMicrocontrollerRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    system_id = get_alarm_system_id_by_user_id(current_user.user_id)

    if system_id is None:
        raise HTTPException(status_code=400, detail="User not paired")

    if not connect_microcontroller_by_user_id(current_user.user_id, request.microcontroller_id):
        raise HTTPException(status_code=400, detail="Connection failed")

    return {
        "status": "ok",
        "alarm_system_id": system_id
    }


@router.post("/api/device/connect", response_model=MicrocontrollerConnectResponse)
def connect_device(
    request: ConnectDeviceRequest,
    user_id: int = Depends(get_current_user_id),
):
    """Link your ESP32 (e.g. esp32_001 = microcontroller_id 1) to your account so real sensor events show in the app."""
    if not get_username_by_user_id(user_id):
        raise HTTPException(status_code=400, detail="User not found.")
    if get_alarm_system_id_by_user_id(user_id) is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Not assigned to a warehouse yet. Pair with your alarm system password first "
                "(Settings in the app), or ask an admin to add your account to a warehouse."
            ),
        )
    if not connect_microcontroller_by_user_id(user_id, request.microcontroller_id):
        raise HTTPException(
            status_code=400,
            detail="Could not link device (database error). Try again.",
        )
    from db.connectToAlarmSystem import get_alarm_system_id_by_user_id
    alarm_system_id = get_alarm_system_id_by_user_id(user_id)
    return {"status": "ok", "alarm_system_id": alarm_system_id or 0}
