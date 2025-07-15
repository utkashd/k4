from typing import Callable, Literal

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
from k4_logger import log
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


def setup() -> None:
    """
    Here we run any version-to-version migrations that need to take place.

    "Why don't you just use SqlAlchemy + Alembic?"

    I think it's easy to forget the advantages of using raw SQL as strings:
        - transparency: we know *exactly* what queries are being run in Postgres
        - trading risks: raw SQL strings feel risky, but abstracted queries carry other
          risks. And if something goes wrong, it's going to be tougher to fix issues
          originating from bad SqlAlchemy vs. bad raw queries
        - inertia: I'll never be able to completely forget about SQL. Might as well stay
          sharp and embrace the low-level

    All that, plus raw SQL is lightweight. ORMs are heavy and the featureset can be
    overwhelming and thus confusing. With raw SQL, everything is deliberate, and I'm
    forced to understand what I'm doing
    """

    MIGRATIONS: list[Callable[..., None]] = []

    log.info(f"Running {len(MIGRATIONS)} migrations")

    for idx, migration in enumerate(MIGRATIONS):
        log.info(f"Starting migration {idx}: {migration.__name__}")
        migration()
        log.info(f"Completed migration {idx}: {migration.__name__}")

    log.info(f"Finished running {len(MIGRATIONS)} migrations")


def main() -> None:
    uvicorn.run(
        app="main:app",  # app=app
        host="0.0.0.0" if is_running_in_docker_container() else "localhost",
        port=8000,
        reload=is_development_environment() and not is_running_in_docker_container(),
    )


if __name__ == "__main__":
    setup()
    main()
