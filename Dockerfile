# syntax=docker/dockerfile:1

# --- builder: resolve dependencies into /app/.venv ---
FROM mcr.microsoft.com/playwright/python:v1.64.1-noble AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 POETRY_VIRTUALENVS_CREATE=true POETRY_VIRTUALENVS_IN_PROJECT=true
WORKDIR /app
RUN python3 -m pip install --upgrade pip poetry
COPY pyproject.toml poetry.lock ./
# Runtime deps only - dev deps stay out of the image
RUN poetry install --only main --no-root

# --- runtime: copy the resolved venv, then the code ---
FROM mcr.microsoft.com/playwright/python:v1.64.1-noble AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
WORKDIR /app
# Dependency layer: changes only when the lockfile changes
COPY --from=builder /app/.venv /app/.venv
COPY . .
# Windows/macOS build contexts carry no exec bit; make the entrypoint runnable
# regardless of where the image is built (Railway's git checkout already has +x)
RUN chmod +x run.sh
# The base image ships browsers+deps; this is a fast no-op/repair step
RUN playwright install chromium
EXPOSE 8000
CMD ["./run.sh"]