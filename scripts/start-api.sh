#!/bin/sh
set -e
python -m gameguard.migrate
exec uvicorn gameguard.api:app --host 0.0.0.0 --port "${PORT:-10000}"
