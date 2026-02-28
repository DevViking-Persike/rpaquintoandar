#!/usr/bin/env bash
# run.sh — Run rpaquintoandar with the given arguments
#
# Usage:
#   bash scripts/run.sh --mode full-crawl --target 1000
#   bash scripts/run.sh --mode resume
#   bash scripts/run.sh --mode test-search
#   bash scripts/run.sh --mode test-listing --listing-id 893456789
#   bash scripts/run.sh --mode full-crawl --city "Rio de Janeiro" --no-headless
#
# All arguments are forwarded to `python -m rpaquintoandar`.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    if [[ -f .venv/bin/activate ]]; then
        source .venv/bin/activate
    else
        echo "Error: No virtual environment found. Run 'bash scripts/setup.sh' first."
        exit 1
    fi
fi

exec python -m rpaquintoandar "$@"
