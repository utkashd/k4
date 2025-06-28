from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import SecretStr

from .dependencies import sessions_manager, users_manager, verify_password

auth_router = APIRouter()


@auth_router.post("/login")
async def login_for_session_id(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> JSONResponse:
    user_email = form_data.username
    unhashed_user_password = SecretStr(form_data.password)

    user = await users_manager.get_active_user_by_email(user_email)

    def is_password_correct(
        unhashed_user_password: SecretStr, hashed_user_password: SecretStr
    ) -> bool:
        return verify_password(
            unhashed_user_password.get_secret_value(),
            hashed_user_password.get_secret_value(),
        )

    if not is_password_correct(
        unhashed_user_password=unhashed_user_password,
        hashed_user_password=user.hashed_user_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session = await sessions_manager.create_session(
        user_id=user.user_id, user_agent="temp", ip_address="temp"
    )

    session_id = str(session.session_id)

    response = JSONResponse({"msg": "Login successful"})
    response.set_cookie(
        key="sessionId",
        value=session_id,
        httponly=True,
        samesite="strict",
    )
    return response


@auth_router.post("/logout")
async def logout() -> JSONResponse:
    response = JSONResponse(content={"msg": "Logout succcessful"})
    response.delete_cookie(
        key="sessionId",
        httponly=True,
        secure=False,
    )
    return response
