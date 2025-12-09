FROM python:3.12-bullseye AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && pip install --no-cache-dir "poetry==${POETRY_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

# Copy only project metadata first for better docker layer caching
COPY pyproject.toml /app/
# Include README for packaging metadata during project install
COPY README.md /app/

# If you later add a poetry.lock, copy it too for deterministic builds
COPY poetry.lock* /app/

RUN poetry install --no-interaction --no-ansi --only main --no-root

# Now copy the actual source
COPY src /app/src

# Install the current project so the console script `azure-devops-mcp` exists
# Use pip to install the local package into the system site-packages (no venv)
RUN pip install --no-cache-dir .

# Set default environment variable names documented in README
ENV MCP_LOG_LEVEL=INFO \
    AZDO_VERIFY_SSL=true \
    AZDO_AUTH_TYPE=pat

# Expose nothing: this MCP uses stdio; container runs as a process
ENTRYPOINT ["azure-devops-mcp"]
