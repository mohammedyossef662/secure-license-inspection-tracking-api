#!/bin/sh
# Apply Alembic migrations and start the API server.
set -e

echo "Applying database migrations..."
python -m alembic upgrade head

echo "Starting Regulatory License & Inspection Tracking API..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
