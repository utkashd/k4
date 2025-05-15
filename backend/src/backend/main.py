import os
from typing import Literal

import uvicorn
from api import (
    chats_router,
    debug_router,
    extensions_router,
    lifespan,
    providers_router,
    setup_router,
    users_router,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils.environment import (
    is_development_environment,
    is_production_environment,
    is_running_in_docker_container,
)

if is_production_environment() and os.getenv("K4_SENTRY_DSN"):
    import sentry_sdk

    sentry_sdk.init(
        # THIS MUST HAPPEN BEFORE app = `FastAPI()`
        dsn=os.getenv("K4_SENTRY_DSN"),
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for tracing.
        traces_sample_rate=1.0,
        _experiments={
            # Set continuous_profiling_auto_start to True
            # to automatically start the profiler on when
            # possible.
            "continuous_profiling_auto_start": True,
        },
    )

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

app.include_router(setup_router)
app.include_router(users_router)
app.include_router(chats_router)
app.include_router(extensions_router)
app.include_router(providers_router)
app.include_router(debug_router)


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
