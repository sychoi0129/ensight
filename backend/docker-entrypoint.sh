#!/bin/sh
set -e

PORT="${PORT:-8000}"

echo "[ensight] starting uvicorn on 0.0.0.0:${PORT} (cwd=$(pwd))"

cd /app/backend
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --log-level info
