FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

# Enable bytecode compilation, Copy from the cache instead of linking since it's a mounted volume
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

# k4 needs a git executable
RUN apt-get update && \
    apt-get install --no-install-recommends -y build-essential git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --no-install-workspace is how to install all the non-internal packages
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-editable --no-install-project --no-install-workspace --no-dev

# See .dockerignore for the backend files that aren't copied
COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# Important: use the python image + version that matches the builder
# Alpine doesn't work because it seems that pydantic_core is incompatible with it
FROM python:3.13-slim-bookworm

# Anthony Sottile says this line should be in every Dockerfile:
ENV LANG=C.UTF-8

# don't run the container as the root user
RUN useradd --create-home appuser
RUN mkdir -p /k4_data && chown -R appuser:appuser /k4_data
USER appuser

# k4 needs a git executable
COPY --from=builder /usr/bin/git /usr/bin/

WORKDIR /app

# add the virtual environment and the git executable to the path
ENV PATH="/app/.venv/bin:/usr/bin:$PATH"

COPY --from=builder /app /app

ENTRYPOINT ["python", "/app/src/backend/main.py"]
