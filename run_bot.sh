#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/syahnur/telegram-monitor-bot"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"

cd "$PROJECT_DIR"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "ERROR: Python executable not found at $PYTHON_BIN" >&2
  exit 1
fi

exec "$PYTHON_BIN" -m src.main
