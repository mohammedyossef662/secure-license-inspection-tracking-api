#!/bin/sh
# Apply Alembic migrations and start the API server.
set -e

echo "Applying database migrations..."
python -m alembic upgrade head

if [ "${SEED_ON_START:-false}" = "true" ]; then
  echo "Seeding demo data..."
  python -m scripts.seed
fi

echo "Starting Regulatory License & Inspection Tracking API..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
