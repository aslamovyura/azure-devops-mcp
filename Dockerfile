# Use a slim base image to reduce size
FROM python:3.12-slim-bullseye AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_VIRTUALENVS_CREATE=false

# Set working directory
WORKDIR /app

# Install dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && pip install --no-cache-dir "poetry==${POETRY_VERSION}" \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata for caching
COPY pyproject.toml poetry.lock* README.md /app/

# Install dependencies with Poetry
RUN poetry install --no-interaction --no-ansi --only main --no-root

# Copy application source code
COPY src /app/src

# Install the project
RUN pip install --no-cache-dir .

# Set default environment variables
ENV MCP_LOG_LEVEL=INFO \
    AZDO_VERIFY_SSL=true \
    AZDO_AUTH_TYPE=pat

# Define entrypoint
ENTRYPOINT ["azure-devops-mcp"]