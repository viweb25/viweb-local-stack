FROM ghcr.io/astral-sh/uv:0.7.13 AS uv
FROM python:3.11-slim AS base
COPY --from=uv /uv /uvx /bin/
WORKDIR /workspace
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace/services/api/src:/workspace/services/worker
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
ENV PATH="/workspace/.venv/bin:$PATH"
COPY packages packages
COPY services services
RUN useradd --uid 10001 --create-home platform && install -d -m 0700 -o platform /var/lib/viweb-demo /var/lib/viweb-training
USER platform
