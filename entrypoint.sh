#!/bin/sh
# Wait for MySQL, apply Alembic migrations and start the API server.
set -e

# On PaaS platforms (Railway, Render, Fly.io) the database can still be starting
# when this container boots. Wait for it so the first migration does not fail.
echo "Waiting for the database..."
python - <<'PY'
import os
import time

from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
last_error = None
for attempt in range(1, 31):
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("Database is ready.")
        break
    except Exception as exc:  # connection refused, DNS not ready, auth race
        last_error = exc
        print(f"Database not ready ({attempt}/30): {exc}")
        time.sleep(2)
else:
    raise SystemExit(f"Database did not become ready in time: {last_error}")
PY

echo "Applying database migrations..."
python -m alembic upgrade head

if [ "${SEED_ON_START:-false}" = "true" ]; then
  echo "Seeding demo data..."
  python -m scripts.seed
fi

echo "Starting Regulatory License & Inspection Tracking API..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
