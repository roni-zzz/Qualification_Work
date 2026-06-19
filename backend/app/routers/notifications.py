from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from app.config import settings
from app.models.request_models import RegisterTokenRequest
from app.models.response_models import SimpleStatusResponse
from app.services.notification_service import register_fcm_token
from db.connectToAlarmSystem import get_alarm_system_id_by_user_id

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

security = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security)
) -> int:
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization")

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=["HS256"],
        )
        return int(payload["userId"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/register", response_model=SimpleStatusResponse)
def register_token(
    request: RegisterTokenRequest,
    user_id: int = Depends(get_current_user_id)
):
    alarm_system_id = get_alarm_system_id_by_user_id(user_id)
    token = (request.token or "").strip()
    print(f"[FCM INLINE REGISTER] user_id={user_id} system={alarm_system_id} token_len={len(token)}")

    if not token:
        raise HTTPException(status_code=400, detail="Empty token")
    lower_token = token.lower()
    if lower_token in {"test_token", "dummy", "placeholder"}:
        raise HTTPException(status_code=400, detail="Invalid token")

    ok, resolved = register_fcm_token(
        alarm_system_id,
        token,
        user_id
    )

    if not ok:
        raise HTTPException(status_code=500, detail="Token save failed")

    return {"status": "ok", "message": "Token registered"}