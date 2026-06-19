#
import time
import jwt
from google.auth import exceptions as google_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

import bcrypt
from app.config import settings
from db.googleAuth import (
    ensure_global_admin_role,
    find_or_create_google_user,
    find_google_user_only,
    get_user_by_email_for_password_login,
)
from app.services.otp_service import generate_otp, send_otp_email, verify_otp

_GOOGLE_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})
_GOOGLE_OAUTH2_CERTS_URL = "https://www.googleapis.com/oauth2/v1/certs"


def _google_oauth_audiences() -> list[str]:
    """OAuth client IDs allowed as ID token `aud` / `azp` (comma-separated in GOOGLE_CLIENT_ID)."""
    raw = (settings.google_client_id or "").strip()
    if not raw:
        raise ValueError(
            "Server GOOGLE_CLIENT_ID is missing. Set it in backend/.env (Web application client ID, "
            "same as Android serverClientId; add Android OAuth client too, comma-separated, if needed)."
        )
    return [p.strip() for p in raw.split(",") if p.strip()]


# Alias for any stale code or typos expecting this name without the leading underscore.
google_oauth_audiences = _google_oauth_audiences


def _token_aud_matches_allowed(claim_aud, allowed: list[str]) -> bool:
    if claim_aud is None:
        return False
    allow = set(allowed)
    if isinstance(claim_aud, str):
        return claim_aud in allow
    if isinstance(claim_aud, list):
        return bool(set(claim_aud) & allow)
    return False


def _google_client_allowed(idinfo: dict, allowed: list[str]) -> bool:
    if _token_aud_matches_allowed(idinfo.get("aud"), allowed):
        return True
    azp = idinfo.get("azp")
    if isinstance(azp, str) and azp in set(allowed):
        return True
    return False


def verify_google_token(id_token_str: str):
    allowed = _google_oauth_audiences()
    request = google_requests.Request()
    idinfo = google_id_token.verify_token(
        id_token_str,
        request,
        audience=None,
        certs_url=_GOOGLE_OAUTH2_CERTS_URL,
    )
    if idinfo.get("iss") not in _GOOGLE_ISSUERS:
        raise google_exceptions.GoogleAuthError(
            f"Wrong issuer: expected one of {_GOOGLE_ISSUERS!r}, got {idinfo.get('iss')!r}"
        )
    if not _google_client_allowed(idinfo, allowed):
        raise ValueError(
            f"Token aud={idinfo.get('aud')!r} azp={idinfo.get('azp')!r} not in GOOGLE_CLIENT_ID. Allowed: {allowed}"
        )
    return idinfo


def build_user_response(user: dict):
    role = user.get("role") or "user"
    uid = user["id"]
    now = int(time.time())
    warehouse_role = user.get("warehouse_role")  # Warehouse role: admin, supervisor, worker, contractor
    if warehouse_role is None:
        try:
            from db.warehouse_roles import get_warehouse_role

            warehouse_role = get_warehouse_role(int(uid))
        except Exception:
            warehouse_role = None

    # Keep platform role aligned for warehouse admins so admin-gated routes work after sign-in.
    if (warehouse_role or "").strip().lower() == "admin":
        try:
            ensure_global_admin_role(int(uid))
        except Exception:
            pass
        role = "admin"

    # Claims required by app.security.get_current_user (sub, iat, exp) for /api/pair, GET /events, etc.
    token = jwt.encode(
        {
            "userId": uid,
            "sub": str(uid),
            "email": user["email"],
            "role": role,
            "warehouse_role": warehouse_role or "",
            "iat": now,
            "exp": now + 7 * 24 * 3600,
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": role,
            "phone": user.get("phone"),
            "warehouse_role": warehouse_role,
        },
    }


def signup_user(idToken: str):
    idinfo = verify_google_token(idToken)
    google_id = idinfo.get("sub")
    email = idinfo.get("email")
    name = idinfo.get("name", email.split("@")[0])
    if find_google_user_only(google_id, email, name):
        raise Exception("Account already exists")
    user = find_or_create_google_user(google_id, email, name)
    return build_user_response(user)


def signin_user(idToken: str):
    idinfo = verify_google_token(idToken)
    google_id = idinfo.get("sub")
    email = idinfo.get("email")
    name = idinfo.get("name", email.split("@")[0])
    user = find_google_user_only(google_id, email, name)
    if not user:
        raise Exception("Account does not exist")
    return build_user_response(user)


def signin_user_mfa(idToken: str):
    idinfo = verify_google_token(idToken)
    google_id = idinfo.get("sub")
    email = idinfo.get("email")
    name = idinfo.get("name", email.split("@")[0])
    user = find_google_user_only(google_id, email, name)
    if not user:
        raise Exception("Account does not exist")
    code = generate_otp(email)
    send_otp_email(email, code)
    return {"mfa_required": True, "email": email}


def verify_otp_and_signin(email: str, code: str):
    if not verify_otp(email, code):
        raise Exception("Invalid or expired code")
    user = find_google_user_only("", email, "")
    if not user:
        raise Exception("User not found")
    return build_user_response(user)


def login_with_password(email: str, password: str):
    """Login for admin-created users (email + password). Returns same shape as Google auth."""
    row = get_user_by_email_for_password_login(email)
    if not row:
        raise Exception("Account does not exist or sign-in method not available")
    user_dict, password_hash = row
    if not bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
        raise Exception("Invalid password")
    return build_user_response(user_dict)
