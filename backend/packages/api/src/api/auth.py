from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import SecretStr

from .dependencies import (
    SECRET_KEY,
    create_long_lived_refresh_token,
    create_short_lived_access_token,
    users_manager,
    verify_password,
)

auth_router = APIRouter()
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30


@auth_router.post("/login")
async def login_for_access_token(
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

    access_token = create_short_lived_access_token(
        data_to_encode={"user": user.model_dump_json()},
        minutes_after_which_access_token_expires=JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    refresh_token = create_long_lived_refresh_token(
        data_to_encode={"user": user.model_dump_json()},
        days_after_which_refresh_token_expires=JWT_REFRESH_TOKEN_EXPIRE_DAYS,
    )

    response = JSONResponse({"msg": "Login successful"})
    response.set_cookie(
        key="authToken",
        value=access_token,
        httponly=True,
        secure=False,  # TODO revisit this
        samesite="strict",
    )
    response.set_cookie(
        key="refreshToken",
        value=refresh_token,
        httponly=True,
        secure=False,  # TODO revisit this
        samesite="strict",
    )
    return response


@auth_router.post("/refresh")
async def refresh_access_token(request: Request) -> JSONResponse:
    """
    When the user's short-lived access token expires, they'll use this endpoint to get a
    new short-lived access token.

    The user sends us their long-lived refresh token, which we'll validate, and then
    we'll check that the user is still active. Then we'll send them a new access token

    Parameters
    ----------
    request : Request
        _description_

    Returns
    -------
    JSONResponse
        _description_

    Raises
    ------
    HTTPException
        _description_
    HTTPException
        _description_
    HTTPException
        _description_
    """
    refresh_token = request.cookies.get("refreshToken")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    try:
        payload = jwt.decode(token=refresh_token, key=SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_email = payload.get("user_email")
    if not user_email or not isinstance(user_email, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unexpected issue encountered when attempting to validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await users_manager.get_active_user_by_email(user_email)

    response = JSONResponse({"msg": "Login successful"})
    new_access_token = create_short_lived_access_token(
        data_to_encode={"user": user.model_dump_json()},
        minutes_after_which_access_token_expires=JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    response.set_cookie(
        key="authToken",
        value=new_access_token,
        httponly=True,
        secure=False,  # TODO revisit this
        samesite="strict",
    )
    return response


@auth_router.post("/logout")
async def logout() -> JSONResponse:
    response = JSONResponse(content={"msg": "Logout succcessful"})
    response.delete_cookie(
        key="authToken",
        httponly=True,
        secure=False,
    )
    response.delete_cookie(
        key="refreshToken",
        httponly=True,
        secure=False,
    )
    return response
