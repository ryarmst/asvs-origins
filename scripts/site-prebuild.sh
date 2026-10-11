#!/bin/sh
set -e
cd "$(dirname "$0")/.."
if [ -x .venv/bin/python ]; then
  .venv/bin/python -m pipeline.build
else
  python3 -m pipeline.build
fi
