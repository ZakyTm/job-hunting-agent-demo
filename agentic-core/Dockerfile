# FIX 1: 3.11-slim, not 3.13-slim.
# LangGraph, LangChain, Telethon, and pydantic-core all have pre-built wheels for 3.11.
# 3.13 lacks wheels for several packages → falls back to compiling from source → fails or takes 15+ min.
FROM python:3.11-slim

# FIX 2: These two vars should always be set in Docker Python images.
# PYTHONDONTWRITEBYTECODE — stops Python writing .pyc files (useless in containers, wastes layer space)
# PYTHONUNBUFFERED       — forces stdout/stderr to flush immediately so 'docker logs' shows output in real time
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps — curl is needed for the healthcheck in docker-compose
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# FIX 3: Add a non-root user.
# Running as root inside a container is a security risk — if a dependency has an RCE vulnerability,
# the attacker lands as root. This creates a restricted 'appuser' instead.
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Copy and install requirements BEFORE copying the rest of the code.
# Docker caches this layer as long as requirements.txt hasn't changed —
# meaning a code-only change won't re-run pip install (saves 2-5 min on rebuilds).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code (your .dockerignore controls what's excluded — see below)
COPY . .

# Switch to non-root user for all runtime operations
USER appuser

EXPOSE 8000

# Use exec form (JSON array), not shell form — ensures signals (SIGTERM from 'docker stop')
# reach uvicorn directly rather than being swallowed by a shell process.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
