from contextlib import asynccontextmanager
import datetime
from fastapi import Depends, FastAPI, HTTPException, status
from jose import JWTError, jwt
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, SecretStr
from user_management import (
    AdminUser,
    NonAdminUser,
    RegisteredUser,
    RegistrationAttempt,
    UsersManagerAsync,
)
from passlib.context import (
    CryptContext,
)  # TODO remove passlib because it's not maintained anymore https://github.com/pyca/bcrypt/issues/684
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)


users_manager: UsersManagerAsync | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        """
        we do this because the `finally` clause will *always* be run, even if there's an
        error somewhere during the `yield`
        """
        global users_manager
        users_manager = await UsersManagerAsync()  # type: ignore[misc]
        yield  # everything above the yield is for startup, everything after is for shutdown
    finally:
        assert isinstance(users_manager, UsersManagerAsync)
        await users_manager.end()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


SECRET_KEY = "18e8e912cce442d5fe6af43a003dedd7cedd7248efc16ac926f21f8f940398a8"
# TODO generate this when we start for the first time and save it to local machine
# Generated with `openssl rand -hex 32`


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_email: EmailStr


pwd_context = CryptContext(schemes=["bcrypt"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_admin_user(token: str = Depends(oauth2_scheme)) -> AdminUser:
    current_user = await get_current_user(token)
    if not isinstance(current_user, AdminUser):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User {current_user.user_email} is not an administrator.",
        )
    return current_user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> AdminUser | NonAdminUser:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
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

    assert isinstance(users_manager, UsersManagerAsync)
    return await users_manager.get_user_by_email(user_email)


@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    # TODO consider swapping for sessions: https://evertpot.com/jwt-is-a-bad-default/
    JWT_EXPIRE_MINUTES = 30
    user_email = form_data.username
    unhashed_user_password = SecretStr(form_data.password)

    assert isinstance(users_manager, UsersManagerAsync)
    user = await users_manager.get_user_by_email(user_email)

    def is_password_correct(
        unhashed_user_password: SecretStr, hashed_user_password: SecretStr
    ) -> bool:
        return pwd_context.verify(
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
        data: dict, minutes_after_which_access_token_expires: int
    ) -> str:
        data_to_encode = data.copy()
        time_access_token_expires = datetime.datetime.now(
            datetime.UTC
        ) + datetime.timedelta(minutes=minutes_after_which_access_token_expires)

        data_to_encode.update({"exp": time_access_token_expires})
        encoded_jwt = jwt.encode(data_to_encode, SECRET_KEY, algorithm="HS256")
        return encoded_jwt

    access_token = create_access_token(
        data={"user_email": user.user_email},
        minutes_after_which_access_token_expires=JWT_EXPIRE_MINUTES,
    )
    return Token(access_token=access_token, token_type="bearer")


class FirstAdminDetails(BaseModel):
    desired_user_email: EmailStr
    desired_user_password: SecretStr = Field(max_length=32)


@app.post("/first_admin")
async def create_first_admin_user(first_admin_details: FirstAdminDetails):
    assert isinstance(users_manager, UsersManagerAsync)
    if await users_manager.get_five_users_async():
        # TODO replace this check with something like:
        # select exists (select * from users where is_user_deactivated=false limit 1) as has_data;
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can't try to create a user through this endpoint because the first user has already been created.",
        )
    hashed_desired_password = SecretStr(
        pwd_context.hash(first_admin_details.desired_user_password.get_secret_value())
    )
    return await users_manager.create_user(
        desired_user_email=first_admin_details.desired_user_email,
        hashed_desired_user_password=hashed_desired_password,
        desired_human_name="admin",
        desired_ai_name="U",
        is_user_an_admin=True,
    )


@app.post("/admin")
async def create_admin_user(
    new_user_details: RegistrationAttempt,
    current_admin_user: AdminUser = Depends(get_current_admin_user),
) -> RegisteredUser:
    assert isinstance(users_manager, UsersManagerAsync)
    hashed_desired_password = SecretStr(
        pwd_context.hash(new_user_details.desired_user_password.get_secret_value())
    )
    return await users_manager.create_user(
        desired_user_email=new_user_details.desired_user_email,
        hashed_desired_user_password=hashed_desired_password,
        desired_human_name=new_user_details.desired_human_name,
        desired_ai_name=new_user_details.desired_ai_name,
        is_user_an_admin=True,
    )


@app.post("/user")
async def create_user(
    new_user_details: RegistrationAttempt,
    current_admin_user: AdminUser = Depends(get_current_admin_user),
) -> RegisteredUser:
    assert isinstance(users_manager, UsersManagerAsync)
    hashed_desired_password = SecretStr(
        pwd_context.hash(new_user_details.desired_user_password.get_secret_value())
    )
    return await users_manager.create_user(
        desired_user_email=new_user_details.desired_user_email,
        hashed_desired_user_password=hashed_desired_password,
        desired_human_name=new_user_details.desired_human_name,
        desired_ai_name=new_user_details.desired_ai_name,
    )


@app.get("/user/me")
async def get_current_user_info(
    current_user: RegisteredUser = Depends(get_current_user),
):
    return current_user


@app.get("/five_users")
async def get_five_users(
    current_admin_user=Depends(get_current_admin_user),
) -> list[RegisteredUser]:
    assert isinstance(users_manager, UsersManagerAsync)
    return await users_manager.get_five_users_async()


def main() -> None:
    """
    This function needs to be beneath all the endpoint definitions.
    """
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
