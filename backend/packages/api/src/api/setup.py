from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, SecretStr

from .dependencies import hash_password, users_manager
from .user_management import RegisteredUser

setup_router = APIRouter()


@setup_router.get("/is_setup_required")
async def does_initial_setup_need_to_be_completed() -> bool:
    return not await users_manager.does_at_least_one_active_admin_user_exist()


class FirstAdminDetails(BaseModel):
    desired_user_email: EmailStr
    desired_user_password: SecretStr = Field(max_length=32)


@setup_router.post("/first_admin")
async def create_first_admin_user(
    first_admin_details: FirstAdminDetails,
) -> RegisteredUser:
    if await users_manager.does_at_least_one_active_admin_user_exist():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can't try to create a user through this endpoint because an admin user has already been created.",
        )
    else:
        hashed_desired_password = SecretStr(
            hash_password(first_admin_details.desired_user_password.get_secret_value())
        )
        return await users_manager.create_user(
            desired_user_email=first_admin_details.desired_user_email,
            hashed_desired_user_password=hashed_desired_password,
            desired_human_name="admin",
            desired_ai_name="U",
            is_user_an_admin=True,
        )
