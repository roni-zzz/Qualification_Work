#
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from app.models.request_models import CreateUserRequest
from app.models.response_models import SimpleStatusResponse
from app.security import AuthenticatedUser, get_current_user
from db.insertIntoDB import insertUserInDB, delete_user_account

router = APIRouter()


@router.post("/api/createUser", response_model=SimpleStatusResponse)
def create_user(request: CreateUserRequest):
    if not insertUserInDB(
        request.username,
        request.email,
        None,
        request.password
    ):
        raise HTTPException(status_code=400, detail="User already exists")

    return {"status": "ok", "message": "User created"}


@router.delete("/api/user/account", response_model=SimpleStatusResponse)
def delete_my_account(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
):
    ok, err = delete_user_account(current_user.user_id)
    if not ok:
        if err == "not_found":
            raise HTTPException(status_code=404, detail="Account not found")
        raise HTTPException(status_code=400, detail="Could not delete account")
    return {"status": "ok", "message": "Account deleted"}
