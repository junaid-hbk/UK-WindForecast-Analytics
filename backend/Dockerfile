
# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install curl for health checks
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application files
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# Create non-root user and grant access to Render secret files
RUN useradd --create-home --uid 10001 appuser \
    && usermod -a -G 1000 appuser \
    && chown -R appuser:appuser /app

USER appuser

# Render provides the PORT environment variable
EXPOSE 10000

# Docker HEALTHCHECK: use CMD, not CMD-SHELL
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/api/v1/health" || exit 1

# Start FastAPI
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
