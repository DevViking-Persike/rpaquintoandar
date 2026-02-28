#!/usr/bin/env bash
# setup.sh — Create venv, install dependencies, and set up Playwright
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "==> Creating Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "==> Upgrading pip..."
pip install --upgrade pip

echo "==> Installing project with dev dependencies..."
pip install -e ".[dev]"

echo "==> Installing Playwright Chromium..."
PLAYWRIGHT_BROWSERS_PATH="$PROJECT_DIR/.browsers" playwright install chromium

echo "==> Creating data directories..."
mkdir -p data/export

echo ""
echo "Setup complete! Activate the venv with:"
echo "  source .venv/bin/activate"
echo ""
echo "Then run:"
echo "  python -m rpaquintoandar --mode test-search"
