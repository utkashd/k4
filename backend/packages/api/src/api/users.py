import datetime

from cyris_logger import log
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from pydantic import EmailStr, SecretStr

from .dependencies import (
    SECRET_KEY,
    get_current_active_admin_user,
    get_current_active_user,
    hash_password,
    users_manager,
    verify_password,
)
from .user_management import AdminUser, RegisteredUser, RegistrationAttempt

users_router = APIRouter()


@users_router.post("/user")
async def create_user(
    new_user_details: RegistrationAttempt,
    current_admin_user: AdminUser = Depends(get_current_active_admin_user),
) -> RegisteredUser:
    hashed_desired_password = SecretStr(
        hash_password(new_user_details.desired_user_password.get_secret_value())
    )
    log.info(
        f"Admin `{current_admin_user.user_email}` is creating a non-admin user. {new_user_details.model_dump_json()}"
    )
    return await users_manager.create_user(
        desired_user_email=new_user_details.desired_user_email,
        hashed_desired_user_password=hashed_desired_password,
        desired_human_name=new_user_details.desired_human_name,
        desired_ai_name=new_user_details.desired_ai_name,
    )


@users_router.delete("/user")
async def deactivate_user(
    user_to_deactivate: RegisteredUser,
    current_admin_user: AdminUser = Depends(get_current_active_admin_user),
) -> None:
    if current_admin_user.user_id == user_to_deactivate.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An admin cannot deactivate their own account. A different admin must do so.",
        )
    await users_manager.deactivate_user(user_to_deactivate)


@users_router.put("/user")
async def reactivate_user(
    user_to_reactivate: RegisteredUser,
    current_admin_user: AdminUser = Depends(get_current_active_admin_user),
) -> None:
    log.info(
        f"Admin `{current_admin_user.user_email}` is reactivating a user. {user_to_reactivate.model_dump_json()}"
    )
    await users_manager.reactivate_user(user_to_reactivate)


@users_router.get("/user")
async def get_users(
    current_admin_user: AdminUser = Depends(get_current_active_admin_user),
) -> list[RegisteredUser]:
    return await users_manager.get_users()


@users_router.get("/user/me")
async def get_current_user_info(
    current_user: RegisteredUser = Depends(get_current_active_user),
) -> RegisteredUser:
    return current_user


@users_router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> JSONResponse:
    # TODO switch to sessions? https://evertpot.com/jwt-is-a-bad-default/
    JWT_EXPIRE_MINUTES = (
        60 * 24  # long only because I plan to remove this in favor of sessions
    )
    user_email = form_data.username
    unhashed_user_password = SecretStr(form_data.password)

    user = await users_manager.get_active_user_by_email(user_email)
    if user.is_user_deactivated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User {user.user_email} is a deactivated user.",
            headers={"WWW-Authenticate": "Bearer"},
        )

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

    def create_access_token(
        data_to_encode: dict[str, EmailStr | datetime.datetime],
        minutes_after_which_access_token_expires: int,
    ) -> str:
        time_access_token_expires = datetime.datetime.now(
            datetime.UTC
        ) + datetime.timedelta(minutes=minutes_after_which_access_token_expires)

        data_to_encode.update({"exp": time_access_token_expires})
        encoded_jwt: str = jwt.encode(data_to_encode, SECRET_KEY, algorithm="HS256")
        return encoded_jwt

    access_token = create_access_token(
        data_to_encode={"user_email": str(user.user_email)},
        minutes_after_which_access_token_expires=JWT_EXPIRE_MINUTES,
    )
    response = JSONResponse({"msg": "Login successful"})
    response.set_cookie(
        key="authToken",
        value=access_token,
        httponly=True,
        secure=False,  # TODO change this to true after setting up HTTPS
        samesite="strict",
        max_age=JWT_EXPIRE_MINUTES * 60,
    )
    return response


@users_router.post("/logout")
async def logout() -> JSONResponse:
    response = JSONResponse(content={"msg": "Logout succcessful"})
    # Overwrite the client's existing `authToken` cookie with an empty/expired one
    response.set_cookie(  # TODO replace with delete cookie
        key="authToken",
        value="",
        httponly=True,
        secure=False,
        expires=0,  # expire the httponly cookie immediately
        max_age=0,
    )
    return response


@users_router.post("/admin")
async def create_admin_user(
    new_user_details: RegistrationAttempt,
    current_admin_user: AdminUser = Depends(get_current_active_admin_user),
) -> RegisteredUser:
    hashed_desired_password = SecretStr(
        hash_password(new_user_details.desired_user_password.get_secret_value())
    )
    log.info(
        f"Admin `{current_admin_user.user_email}` is creating an admin user. {new_user_details.model_dump_json()}"
    )
    return await users_manager.create_user(
        desired_user_email=new_user_details.desired_user_email,
        hashed_desired_user_password=hashed_desired_password,
        desired_human_name=new_user_details.desired_human_name,
        desired_ai_name=new_user_details.desired_ai_name,
        is_user_an_admin=True,
    )
