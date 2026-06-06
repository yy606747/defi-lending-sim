#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

if command -v python3 >/dev/null 2>&1; then
  exec python3 main.py --config demo.yaml
fi

exec python main.py --config demo.yaml
