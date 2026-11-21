# Regulatory License & Inspection Tracking API

A secure REST API for tracking regulated facilities, their licenses and inspection
records.

- **Framework:** Python 3.12 / FastAPI / Uvicorn
- **Database:** MySQL 8 (SQLAlchemy ORM + Alembic migrations)
- **Auth:** JWT (HS256, short-lived access tokens) + Argon2id password hashing
- **RBAC:** Admin (full access) / Inspector (own inspections only) / Viewer (read-only)
- **Audit:** append-only audit log for security-relevant events

---

## Quick start (Docker Compose)

```bash
cp .env.example .env
docker compose up --build
```

The API is then available at <http://localhost:8000> and the health check at
<http://localhost:8000/health>.

## Website

The app serves a role-aware web console at **`/`** (`docs/index.html` plus
`docs/assets/`) — no framework or CDN, so it satisfies the app's strict
`Content-Security-Policy`. Sign in with an account created by an administrator
(`python -m scripts.seed` provisions demo data) to get:

- **Dashboard** — facility, license and inspection totals, licenses expiring
  within 30 days, and recent compliance activity.
- **Facilities, Licenses, Inspections** — searchable, filterable, paginated
  tables. Admins get create/edit/delete dialogs; inspectors can record and
  update their own inspections; viewers are read-only.
- **Users and Audit log** (admin only) — manage accounts and inspect the
  immutable audit trail with action/entity/user/date filters.
- **My profile** and **About this API** — update your account and read the
  project overview.

The JWT lives in `sessionStorage` and is cleared on logout or expiry. The
sign-in screen keeps the project overview and links to the GitHub repository
and the committed OpenAPI schema (`openapi.json`). Assets are served from
`/assets/`; the JSON service descriptor is at `/api`.

**On GitHub:** the repository hosts the project documentation — `README.md`,
the API reference `docs/07-api-reference.md`, and the full generated OpenAPI
schema `openapi.json` (committed from the app via `FastAPI.openapi()`). The project stands alone without Swagger: `DOCS_ENABLED=false` (the default)
makes `/docs`, `/redoc` and `/openapi.json` return 404.

**On GitHub Pages:** the `Deploy GitHub Pages` workflow publishes the `docs/`
folder to <https://mohammedyossef662.github.io/secure-license-inspection-tracking-api/>
on pushes to `main`. In **Settings → Pages**, set the build and deployment
source to **GitHub Actions**. Pages can only host static files, so that copy
shows a preview notice and disables sign-in; run the API (locally or on any
container host) and open its root URL to use the full console.

## Quick start (local development)

```bash
python -m venv .venv
.\.venv\Scripts\activate        # Windows
source .venv/bin/activate       # Linux / macOS
pip install -r requirements-dev.txt
cp .env.example .env
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

Run the test suite:

```bash
python -m pytest --cov=app
python -m ruff check .
python -m ruff format --check .
python -m bandit -r app -ll
python -m pip_audit -r requirements.txt
```

## Configuration

All runtime settings are supplied through environment variables (see
`.env.example`). Required in production: `SECRET_KEY`, `DATABASE_URL` (MySQL),
`ALLOWED_HOSTS`, `ALLOWED_ORIGINS`.

## API overview

| Area | Method | Path | Auth | Description |
|---|---|---|---|---|
| Website | GET | `/` | Public | Web console / sign-in page (live API status, docs links) |
| Operations | GET | `/health` | Public | Liveness / readiness check |
| Operations | GET | `/api` | Public | Service descriptor (name, version, docs URLs) |
| Auth | POST | `/auth/login` | Public | Obtain JWT access token |
| Auth | POST | `/auth/logout` | Bearer | Revoke the current access token |
| Users | GET | `/users/me` | Bearer | Current user profile |
| Users | PUT | `/users/me` | Bearer | Update own profile / change password |
| Users | POST | `/users` | Admin | Create user |
| Users | GET | `/users` | Admin | List users (paginated, searchable) |
| Users | GET | `/users/{id}` | Admin | Read user |
| Users | PUT | `/users/{id}` | Admin | Update user / role / status / password |
| Users | DELETE | `/users/{id}` | Admin | Deactivate user |
| Facilities | GET | `/facilities` | Bearer | List facilities (search / filter / paginate) |
| Facilities | POST | `/facilities` | Admin | Create facility |
| Facilities | GET | `/facilities/{id}` | Bearer | Read facility |
| Facilities | PUT | `/facilities/{id}` | Admin | Update facility |
| Facilities | DELETE | `/facilities/{id}` | Admin | Soft delete facility (blocked while active licenses exist) |
| Licenses | GET | `/licenses` | Bearer | List licenses (filters incl. expired) |
| Licenses | POST | `/licenses` | Admin | Create license |
| Licenses | GET | `/licenses/{id}` | Bearer | Read license |
| Licenses | PUT | `/licenses/{id}` | Admin | Update license |
| Licenses | DELETE | `/licenses/{id}` | Admin | Soft delete (revoke) license |
| Inspections | GET | `/inspections` | Bearer | List inspections (filters / pagination) |
| Inspections | POST | `/inspections` | Staff | Record inspection (Inspector: own records only) |
| Inspections | GET | `/inspections/{id}` | Bearer | Read inspection |
| Inspections | PUT | `/inspections/{id}` | Bearer | Update (Admin: any; Inspector: own only) |
| Audit logs | GET | `/audit-logs` | Admin | Query audit log |

## Security headers

Responses include: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Referrer-Policy: no-referrer`, `Permissions-Policy`, `Cross-Origin-*`, 
`X-Permitted-Cross-Domain-Policies: none`, `Cache-Control: no-store`, CSP,
`Strict-Transport-Security` (when enabled), `X-Request-ID` (always).

## Error format

All errors return JSON: `{ "detail": "..." }` — no stack traces, SQL errors or
input echoes.

## Deploy as a website

The app is a self-contained Docker image (API + web console), so any
container host works. Two one-click options:

**Render (blueprint — API + MySQL included)**

1. Connect this repository in the Render dashboard.
2. Choose **New +** → **Blueprint** and select `render.yaml`.
3. Render builds the image, provisions MySQL, runs `alembic upgrade head` and
   serves the site at `https://<name>.onrender.com`.

**Fly.io**

```bash
fly launch --no-deploy
fly secrets set DATABASE_URL="mysql+pymysql://user:pass@host/db"
fly secrets set SECRET_KEY="$(openssl rand -hex 32)"
fly deploy
```

**Any other host / GHCR**

`.github/workflows/docker.yml` builds and pushes the image to
`ghcr.io/<owner>/<repo>` on every push to `main`, so it can be deployed to
Railway, AWS, Azure, a VPS, etc.

Before going public set production values: `SECRET_KEY`, `DATABASE_URL`,
`ENVIRONMENT=production`, `ALLOWED_HOSTS`, `ALLOWED_ORIGINS`. Swagger UI is
disabled by default (`DOCS_ENABLED=false`).

## Docs

- Requirements: `docs/01-requirements.md`
- Architecture: `docs/02-architecture.md`
- Threat model: `docs/03-threat-model.md`
- Test plan: `docs/04-test-plan.md`
- Test report: `docs/05-test-report.md`
- Deployment: `docs/06-deployment.md`
- API reference: `docs/07-api-reference.md`

## License

MIT — see [LICENSE](LICENSE).
