from fastapi import APIRouter, HTTPException
from app.models.response_models import AuthResponse
from app.models.request_models import GoogleAuthRequest, OtpVerifyRequest, EmailPasswordLoginRequest
from app.services.auth_service import signup_user, verify_otp_and_signin, signin_user, login_with_password


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse)
def signup(request: GoogleAuthRequest):
    try:
        return signup_user(request.idToken)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/signin", response_model=AuthResponse)
def signin(request: GoogleAuthRequest):
    """Google sign-in (no MFA — OTP flow disabled until SMTP is configured)."""
    try:
        return signin_user(request.idToken)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify-otp", response_model=AuthResponse)
def verify_otp(request: OtpVerifyRequest):
    try:
        return verify_otp_and_signin(request.email, request.code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=AuthResponse)
def login(request: EmailPasswordLoginRequest):
    """Email/password login for admin-created warehouse manager accounts."""
    try:
        return login_with_password(request.email.strip(), request.password)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
