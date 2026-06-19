from pydantic import BaseModel
from typing import Optional


class SimpleStatusResponse(BaseModel):
    status: str
    message: str  # Added this field


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: Optional[str] = "user"
    phone: Optional[str] = None
    warehouse_role: Optional[str] = None


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class MicrocontrollerConnectResponse(BaseModel):
    status: str
    alarm_system_id: int


class HealthResponse(BaseModel):
    status: str
    service: str
    backend_url: Optional[str]

class MfaRequiredResponse(BaseModel):
    mfa_required: bool
    email: str