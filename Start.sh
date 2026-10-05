#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")" || exit 1
echo "Starting Fantasy Lineup Optimizer..."
if command -v python3 >/dev/null 2>&1; then
  exec python3 launch.py
elif command -v python >/dev/null 2>&1; then
  exec python launch.py
else
  echo ""
  echo "ERROR: Python 3.9+ was not found."
  echo "Install Python from https://www.python.org/downloads/ then try again."
  echo ""
  exit 1
fi
