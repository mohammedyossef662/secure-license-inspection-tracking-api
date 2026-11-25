# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial public release of the Regulatory License & Inspection Tracking API.
- FastAPI application with JWT (HS256) authentication, Argon2id password hashing,
  RBAC (admin / inspector / viewer) and broken-object-level-authorization prevention.
- Endpoints for users, facilities, licenses, inspections and audit logs with
  filtering, search and pagination.
- Security hardening middleware (security headers, CSP, HSTS, CORS, trusted host,
  request IDs, generic error handling, login rate limiting).
- Append-only audit log for login attempts, denials and data mutations.
- Alembic migrations and Docker Compose stack (API + MySQL 8).
- Automated test suite (`tests/unit`, `tests/integration`, `tests/security`) with
  `pytest`, `pytest-cov`, targeting at least 80% coverage.
- CI pipeline with Ruff, Bandit, pip-audit and pytest against MySQL 8.
- OWASP hardening controls: explicit access-token revocation via `POST /auth/logout`
  (token denylist until expiry), password complexity policy (min length plus
  upper/lower/digit/special), and request body size limit (64 KiB).
- PaaS deployment: `railway.toml` (Docker + MySQL, automatic HTTPS) and a
  corrected `render.yaml` that uses an external MySQL database, documented in
  `docs/09-paas-deployment.md`.
- The container entrypoint now waits for MySQL to accept connections before
  running migrations, so PaaS boot order no longer causes a crash loop.

### Changed

- Password policy now requires a minimum of 12 characters containing upper case,
  lower case, digit and special character (login keeps legacy-password leniency).

## [0.1.0] - 2026-11-20

### Added

- First implementation of the functional requirements (FR-01 … FR-12).
- First implementation of the security requirements (SR-01 … SR-13).
- Initial database schema migration (`0001_initial`).
- Development seed script (`python -m scripts.seed`).

[Unreleased]: https://github.com/mohamedyossef963/license-inspection-api/compare/0.1.0...HEAD
[0.1.0]: https://github.com/mohamedyossef963/license-inspection-api/releases/tag/0.1.0
