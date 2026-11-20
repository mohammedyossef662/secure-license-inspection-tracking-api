# Deployment

**Project:** Regulatory License & Inspection Tracking API
**Version:** 0.1
**Related documents:** `02-architecture.md`, `.env.example`, `docker-compose.yml`

---

## 1. Deployment targets

| Target | Database | Notes |
|---|---|---|
| Local development | SQLite (file) or Docker MySQL 8 | `DATABASE_URL=sqlite+pysqlite:///./dev.db` |
| Production / staging | MySQL 8 | Docker Compose service `db` (mysql:8.4) |

The application refuses to start with an invalid configuration in the
`production` environment (see `app/core/config.py` production guards).

---

## 2. Docker Compose deployment

```bash
cp .env.example .env
# edit .env: SECRET_KEY, MYSQL_* credentials, ALLOWED_HOSTS, ALLOWED_ORIGINS
docker compose up --build -d
docker compose logs -f api
docker compose down
```

Services:

- `db`: MySQL 8.4 with healthcheck; data persisted in the `mysql_data` volume.
- `api`: built from `Dockerfile`; runs `alembic upgrade head` then starts
  `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

Ports: API `8000/tcp`, database `3306/tcp` (optional host binding).

---

## 3. Environment variables

| Variable | Required | Default | Description |
|---|---:|---:|---|
| `DATABASE_URL` | Yes | – | SQLAlchemy URL, e.g. `mysql+pymysql://appuser:momo@127.0.0.1:3306/license_inspection` |
| `SECRET_KEY` | Yes (production) | – | JWT signing secret, ≥ 32 chars, no placeholder |
| `ENVIRONMENT` | No | `development` | `development` / `test` / `production` |
| `DEBUG` | No | `false` | Debug mode (development only) |
| `DOCS_ENABLED` | No | `true` | OpenAPI / Swagger / ReDoc availability |
| `LOG_LEVEL` | No | `INFO` | Log level |
| `JWT_ISSUER` | No | `license-inspection-api` | JWT issuer claim |
| `JWT_AUDIENCE` | No | `license-inspection-api-clients` | JWT audience claim |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` | Access token lifetime |
| `ALLOWED_ORIGINS` | Prod | – | Comma-separated CORS allow-list, e.g. `https://app.example.com` |
| `ALLOWED_HOSTS` | Prod | – | Comma-separated host allow-list, e.g. `api.example.com,localhost` |
| `TRUST_PROXY_HEADERS` | No | `false` | Honour `X-Forwarded-*` headers |
| `ENABLE_HSTS` | No | `false` | Enable HSTS |
| `LOGIN_RATE_LIMIT_ATTEMPTS` | No | `5` | Max failed logins per window |
| `LOGIN_RATE_LIMIT_WINDOW_SECONDS` | No | `60` | Rate-limit window |
| `LOGIN_RATE_LIMIT_IP_MULTIPLIER` | No | `5` | Per-IP multiplier |
| `SEED_ON_START` | No | `false` | Run seed script on container start |

---

## 4. Running migrations

```bash
python -m alembic upgrade head
python -m alembic downgrade -1
```

Migrations are applied automatically by the Docker entrypoint.

---

## 5. Production checklist

- [ ] `ENVIRONMENT=production`
- [ ] `DATABASE_URL` points to MySQL 8
- [ ] `SECRET_KEY` is a long random value
- [ ] `ALLOWED_HOSTS` restricted
- [ ] `ALLOWED_ORIGINS` set to real origins
- [ ] `ENABLE_HSTS=true`, `TRUST_PROXY_HEADERS=true` behind TLS terminator
- [ ] `DEBUG=false`, `DOCS_ENABLED=false` (or restricted network)
- [ ] TLS termination at reverse proxy / load balancer
- [ ] Database backup schedule

---

## 6. Operations

- Health endpoint: `GET /health` (liveness + readiness, DB check → 503 when degraded).
- Logs: structured-ish JSON-friendly text logs via `app.core.logging`.
- Monitoring: request ID correlation, security headers and status codes in access logs.

---

## 7. Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-11-20 | Mohamed Yossef | Initial deployment guide |
