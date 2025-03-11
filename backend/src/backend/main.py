import os
from typing import Literal

import uvicorn
from api import chats_router, extensions_router, lifespan, setup_router, users_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils import is_development_environment, is_production_environment

if is_production_environment() and os.getenv("CYRIS_SENTRY_DSN"):
    import sentry_sdk

    sentry_sdk.init(
        # THIS MUST HAPPEN BEFORE app = `FastAPI()`
        dsn=os.getenv("CYRIS_SENTRY_DSN"),
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
    ],  # (protocol, domain, port) defines an origin
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PUT"],
    allow_headers=["*"],
)

app.include_router(setup_router)
app.include_router(users_router)
app.include_router(chats_router)
app.include_router(extensions_router)


@app.get("/")
async def am_i_alive() -> Literal[True]:
    return True


def main() -> None:
    uvicorn.run(
        app="main:app",  # app=app
        host="127.0.0.1",  # localhost only, not 0.0.0.0
        port=8000,
        reload=is_development_environment(),
    )


if __name__ == "__main__":
    main()
