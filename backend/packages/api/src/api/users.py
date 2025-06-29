from fastapi import APIRouter, Depends, HTTPException, status
from k4_logger import log
from pydantic import SecretStr

from ._dependencies import (
    get_current_active_admin_user,
    get_current_active_user,
    hash_password,
    users_manager,
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
