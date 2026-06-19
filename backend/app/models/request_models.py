from pydantic import BaseModel, EmailStr, Field


class GoogleAuthRequest(BaseModel):
    idToken: str


class EmailPasswordLoginRequest(BaseModel):
    email: str
    password: str


class RegisterTokenRequest(BaseModel):
    token: str = Field(min_length=20, max_length=4096)


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class PairUserRequest(BaseModel):
    username: str | None = None
    system_password: str = Field(min_length=8)


class ConnectMicrocontrollerRequest(BaseModel):
    username: str | None = None
    microcontroller_id: int = Field(gt=0)


class ConnectDeviceRequest(BaseModel):
    """Link ESP32 to current user's alarm system (JWT). Default device_id esp32_001 -> microcontroller_id 1."""
    microcontroller_id: int = 1

class SimpleStatusResponse(BaseModel):
    status: str
    message: str

class OtpVerifyRequest(BaseModel):
    email: str
    code: str

class MfaRequiredResponse(BaseModel):
    mfa_required: bool
    email: str

# Admin-only request bodies
class AddWarehouseRequest(BaseModel):
    """Optional fixed ESP / microcontroller id so DB matches firmware DEVICE_ID (e.g. esp32_2 → id 2)."""

    microcontroller_id: int | None = Field(
        default=None,
        ge=1,
        le=999_999,
        description="If set, create this board id; must not already exist. Omit for next auto id.",
    )


class SetSensorLabelsRequest(BaseModel):
    labels: list[str]  # e.g. ["Front door", "Back door", "Living room window"]


class AddUserToWarehouseRequest(BaseModel):
    username: str
    email: str
    password: str
    phone: str | None = None
    warehouse_role: str | None = Field(
        default=None,
        description="admin | supervisor | worker | contractor (first user in a warehouse is always admin)",
    )


class LinkExistingUserToWarehouseRequest(BaseModel):
    """Link an account that already exists (e.g. signed up with Google) to this warehouse."""

    email: str
    password: str | None = Field(
        default=None,
        description="Optional. If set (min 8 chars), user can log in with email/password too.",
    )
    warehouse_role: str | None = Field(
        default=None,
        description="admin | supervisor | worker | contractor (first user in warehouse becomes admin)",
    )


class NotifyManagerRequest(BaseModel):
    title: str
    body: str


class UpdateAlarmSystemRequest(BaseModel):
    name: str


class UpdateUserRequest(BaseModel):
    username: str | None = None
    email: str | None = None
    phone: str | None = None
    password: str | None = None
    warehouse_role: str | None = None
