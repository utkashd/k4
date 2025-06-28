from typing import Literal

import uvicorn
from api import (
    auth_router,
    chats_router,
    extensions_router,
    lifespan,
    providers_router,
    setup_router,
    users_router,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils.environment import is_development_environment, is_running_in_docker_container

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],  # (protocol, domain, port) identifies an origin
    # allow_origin_regex="^http://192\.168\..*:5173$",
    # TODO figure out what the correct CORS policy is
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(setup_router)
app.include_router(users_router)
app.include_router(chats_router)
app.include_router(extensions_router)
app.include_router(providers_router)


@app.get("/")
async def am_i_alive() -> Literal[True]:
    return True


def main() -> None:
    uvicorn.run(
        app="main:app",  # app=app
        host="0.0.0.0" if is_running_in_docker_container() else "localhost",
        port=8000,
        reload=is_development_environment() and not is_running_in_docker_container(),
    )


if __name__ == "__main__":
    main()
