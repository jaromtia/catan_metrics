# Backend: FastAPI + uvicorn served via the `catan serve` console script.
# Uses the official uv image which bundles Python 3.14 + uv.
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

# Build the venv in /app/.venv, copy (don't hardlink) so it works across layers,
# and pre-compile bytecode for faster cold starts.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    CATAN_DB=/data/catan.db

# Install dependencies first (cached unless lockfile changes), without the
# project itself or dev/test extras.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Now add the package source and install the project (provides `catan`).
COPY catan ./catan
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Persist the event-sourced SQLite log on a volume so games survive restarts.
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

CMD ["catan", "serve", "--host", "0.0.0.0", "--port", "8000"]
