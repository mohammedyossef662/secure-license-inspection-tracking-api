# Architecture

**Project:** Regulatory License & Inspection Tracking API
**Version:** 0.1
**Related documents:** `01-requirements.md`, `03-threat-model.md`, `06-deployment.md`

---

## 1. Overview

The system is a single FastAPI service written in Python 3.12. The service
exposes a versioned REST API, persists data through SQLAlchemy ORM models and
uses Alembic for schema migrations. There is no separate application server or
background worker; state changes are performed synchronously during the request
lifecycle.

```
Client (SPA / mobile / server-to-server)
        │ HTTPS / JSON / Bearer JWT
        ▼
FastAPI app (middleware -> exception handlers -> routers)
        │ SQLAlchemy (parameterized) -> MySQL 8
        ▼
MySQL 8
```

---

## 2. High-level components

| Component | Location | Responsibility |
|---|---|---|
| App factory | `app/main.py` | Builds the FastAPI instance, wires middleware, routers, exception handlers, lifespan |
| Configuration | `app/core/config.py` | Environment-driven settings with production guards |
| Database engine / session | `app/core/database.py` | SQLAlchemy engine + session factory, request-scoped session lifecycle |
| Middleware | `app/core/middleware.py` | Security headers, CSP, HSTS, request ID, logging, generic 500 |
| Error handling | `app/core/errors.py` | Consistent JSON error responses (no leak of internals) |
| Rate limiting | `app/core/rate_limit.py` | Sliding-window login limiter (in-process) |
| Auth dependencies | `app/auth/dependencies.py` | JWT decode, RBAC (`require_roles`), current user resolution |
| Password hashing | `app/auth/password.py` | Argon2id hashing / verification / dummy-hash timing equalisation |
| Tokens | `app/auth/tokens.py` | Signed JWT creation / strict validation (iss / aud / exp / nbf / sub / jti) |
| Audit service | `app/services/audit.py` | Audit event recording, isolated writes for failures and denials |
| Models | `app/models/` | ORM entities: users, facilities, licenses, inspections, audit_logs |
| Schemas | `app/schemas/` | Pydantic request/response validation with `extra="forbid"` |

---

## 3. Request lifecycle

1. **Middleware chain** (outer → inner): trusted host → CORS → security headers → request context → exception handling.
2. **Routing** resolves the path/method; unmatched → 404, wrong method → 405.
3. **Dependencies** resolve auth, RBAC, pagination, database session.
4. **Handlers** validate payloads via Pydantic (unknown fields rejected, all values bounded).
5. **ORM** performs parameterized queries only.
6. **Audit** writes are committed in the same transaction or in isolated transactions for failed logins / denials.
7. **Response** is serialised through Pydantic response models.

---

## 4. Database design

- ORM models: `User`, `Facility`, `License`, `Inspection`, `AuditLog`.
- Soft delete (`is_deleted`, `deleted_at`) is used for facilities and licenses so the audit trail and historical inspections remain intact.
- Foreign keys use `RESTRICT` (facilities/licenses/inspections) and `SET NULL` (audit user) semantics.
- Check constraints: license `expiry_date > issue_date`.
- Enum columns are backed by SQLAlchemy `Enum` with `native_enum=False` and a CHECK constraint so the same schema works on MySQL and SQLite.

---

## 5. Authentication and authorization design

- Tokens are signed JWT access tokens with `sub`, `username`, `role`, `iat`, `nbf`, `exp`, `iss`, `aud`, `jti`.
- Access token lifetime is 15 minutes by default (configurable).
- **The role used for authorization is read from the database**, never from the token claim alone, so a stale or forged claim cannot escalate privileges.
- Inspectors may create inspections only for themselves; they may update only their own inspections (BOLA prevention).
- Admins may update any inspection.

---

## 6. Security design decisions

- Passwords hashed with Argon2id (argon2-cffi) with a dummy hash for unknown users to reduce timing-based enumeration.
- Login rate limiting: sliding window per `ip:username` and per `ip` scope; successful login clears the account scope.
- Validation errors never echo submitted values (no password / token leakage); error shape is `{ "detail": [...] }` with `loc`/`msg`/`type` only.
- Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-*`, `X-Permitted-Cross-Domain-Policies`, `Cache-Control: no-store`, CSP (API strict, docs relaxed), HSTS when enabled, `X-Request-ID` correlation, no `Server` / `X-Powered-By` headers.

---

## 7. Testing overview

See `04-test-plan.md` and `05-test-report.md`. Three automated layers: unit, integration, security.

---

## 8. Deployment overview

See `06-deployment.md`.

---

## 9. Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-11-20 | Mohamed Yossef | Initial architecture |
