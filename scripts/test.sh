#!/usr/bin/env bash
# test.sh — Run tests and optional linting/type checks
#
# Usage:
#   bash scripts/test.sh          # pytest only
#   bash scripts/test.sh --all    # pytest + ruff + mypy (if available)
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

echo "==> Running pytest..."
pytest -v

if [[ "${1:-}" == "--all" ]]; then
    if command -v ruff &>/dev/null; then
        echo ""
        echo "==> Running ruff check..."
        ruff check src/ tests/
    else
        echo ""
        echo "(skipping ruff — not installed)"
    fi

    if command -v mypy &>/dev/null; then
        echo ""
        echo "==> Running mypy..."
        mypy src/
    else
        echo ""
        echo "(skipping mypy — not installed)"
    fi
fi

echo ""
echo "Done."
