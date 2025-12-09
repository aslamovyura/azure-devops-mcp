#!/usr/bin/env bash
set -euo pipefail

# Wrapper to launch the MCP server via docker compose.
# Requires docker and docker compose. Uses .env for configuration.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${SCRIPT_DIR%/bin}"

cd "$ROOT_DIR"

exec docker compose run --rm azure-devops-mcp "$@"

