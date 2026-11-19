
# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install curl for the container health check.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application files.
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# Create a non-root user with access to Render secret files.
RUN useradd --create-home --uid 10001 appuser \
    && usermod -a -G 1000 appuser \
    && chown -R appuser:appuser /app

# Run the application as a non-root user.
USER appuser

# Render supplies the PORT environment variable.
EXPOSE 10000

# Container health check.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD-SHELL curl -fsS "http://127.0.0.1:${PORT:-8000}/api/v1/health" || exit 1

# Start FastAPI using Uvicorn.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
