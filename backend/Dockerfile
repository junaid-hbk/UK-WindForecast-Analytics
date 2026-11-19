
# Use Python 3.12 slim image
FROM python:3.12-slim

# Python environment settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Set working directory
WORKDIR /app

# Install curl for Render health checks
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

# Create group with GID 1000 for Render Secret File access.
# Create a non-root application user using that group.
RUN groupadd --gid 1000 render-group \
    && useradd --create-home --uid 10001 --gid 1000 appuser \
    && chown -R appuser:render-group /app

# Run application as non-root user
USER appuser

# Render uses the PORT environment variable
EXPOSE 10000

# Application health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-10000}/api/v1/health" || exit 1

# Start FastAPI application
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
