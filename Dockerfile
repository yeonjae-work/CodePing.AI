# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps separately to leverage layer cache
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Expose API port
EXPOSE 8000

# Default environment (can be overridden)
ENV GITHUB_WEBHOOK_SECRET=mydevsecret \
    DATABASE_URL=sqlite+aiosqlite:///./dev.db \
    CELERY_ALWAYS_EAGER=true

# Launch application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 