FROM python:3.12-slim-bookworm

ARG DEBIAN_PACKAGES="build-essential curl"

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/home/app/.venv

RUN set -ex; \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends $DEBIAN_PACKAGES && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip && \
    pip install uv && \
    useradd -ms /bin/bash app -d /home/app -u 1000 && \
    mkdir -p /app /app/model-cache && \
    chown -R app:app /app

USER app
WORKDIR /app

COPY --chown=app:app inference/pyproject.toml inference/uv.lock* ./
RUN uv sync --frozen

COPY --chown=app:app shared/ ./shared/
COPY --chown=app:app prompts/ ./prompts/
COPY --chown=app:app inference/ ./inference/

ENV PYTHONPATH=/app
EXPOSE 8001
CMD ["/home/app/.venv/bin/uvicorn", "inference.server:app", "--host", "0.0.0.0", "--port", "8001"]
