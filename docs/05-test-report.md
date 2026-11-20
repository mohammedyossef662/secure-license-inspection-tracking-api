# Test Report

**Project:** Regulatory License & Inspection Tracking API
**Version:** 0.1
**Author:** Mohamed Yossef Mohamed
**Date:** 2026-11-20
**Related documents:** `04-test-plan.md`, `01-requirements.md`, `03-threat-model.md`

---

## 1. Executive summary

The automated test suite for the Regulatory License & Inspection Tracking API was executed
locally on 2026-11-20 and in CI against a MySQL 8.4 instance.

**Result: 140 tests passed, 0 failed.**

The suite covers unit tests, integration tests (against a real database) and security tests
(authorization, BOLA, injection, token hardening, headers and error handling).

---

## 2. Test environment

| Item | Detail |
|---|---|
| Python | 3.14.6 (project target: 3.12; CI runs 3.12) |
| Database | MySQL 8.4.13 running in Docker (`mysql-local`, healthy) |
| Test database | `license_inspection` (schema created by Alembic `0001_initial`) |
| ORM | SQLAlchemy 2.1, Alembic 1.20 |
| HTTP client | FastAPI `TestClient` (httpx) |
| Coverage | `pytest-cov`, source `app`, branch coverage enabled |

---

## 3. Automated test results

### 3.1 Unit tests (`tests/unit/`)

| File | Tests | Result |
|---|---:|---|
| `test_password.py` | Password hashing / Argon2id / dummy verification | Pass |
| `test_tokens.py` | JWT create / decode, expiry, tampering, audience, issuer, alg-none, missing claim | Pass |
| `test_rate_limit.py` | Sliding-window rate limiter behaviour | Pass |
| `test_schemas.py` | Field validation / normalisation / unknown-field rejection | Pass |
| `test_config.py` | Settings parsing, production guards | Pass |

**Unit result: 15 passed**

### 3.2 Integration tests (`tests/integration/`)

| File | Tests | Result |
|---|---:|---|
| `test_auth.py` | Login (JSON + form), invalid credentials, inactive user, malformed tokens, validation secrets, rate limit, audit | Pass |
| `test_users.py` | User CRUD, role updates, self-protection, profile update, password change, mass assignment | Pass |
| `test_facilities.py` | Facility CRUD, duplicates, search/filter/pagination, soft delete, active-license guard | Pass |
| `test_licenses.py` | License CRUD, date validation, filters, expiry flag, revoke | Pass |
| `test_inspections.py` | Inspection CRUD, filters, validation, ownership rules | Pass |
| `test_audit_logs.py` | Audit population, filters, pagination, validation | Pass |
| `test_health.py` | Health, OpenAPI, root, docs | Pass |

**Integration result: 72 passed**

### 3.3 Security tests (`tests/security/`)

| File | Tests | Result |
|---|---:|---|
| `test_rbac.py` | Viewer/inspector admin action denials, unauthenticated protection, denial auditing | Pass |
| `test_bola.py` | Inspector ownership enforcement, admin override, mass assignment | Pass |
| `test_injection.py` | SQL injection, wildcard handling, mass assignment, type confusion, path injection, pagination limits | Pass |
| `test_tokens.py` | Expired / not-yet-valid / tampered / wrong-key / wrong-aud / alg-none / missing-claim / unknown-user tokens, DB-role enforcement | Pass |
| `test_headers_and_errors.py` | Security headers, CSP, HSTS, trusted host, CORS, request ID, generic 500, docs disabled, 404/405, validation secret handling | Pass |

**Security result: 46 passed**

### 3.4 Totals

| Layer | Tests | Passed | Failed |
|---|---:|---:|---:|
| Unit | 21 | 21 | 0 |
| Integration | 73 | 73 | 0 |
| Security | 46 | 46 | 0 |
| **Total** | **140** | **140** | **0** |

### 3.5 Coverage

```
Name                         Stmts   Miss Branch BrPart  Cover   Missing
--------------------------------------------------------------------
app\auth\revocation.py         24      4      4      1    82%   39-40, 44-45
app\core\config.py            63      1     10      1    97%   68
app\core\database.py          27      0      4      1    97%   31->39
app\core\errors.py           27      6      2      0    79%   39-46, 53-60
app\core\middleware.py        61      5     10      3    86%   37-39, 105, 107
app\core\rate_limit.py       61      5     20      1    90%   77, 89-92
app\routers\auth.py           68      1     14      1    98%   153
app\routers\facilities.py    78      0     20      2    98%   124->129, 188->195
app\routers\inspections.py   78      1     32      1    98%   100
app\routers\licenses.py      86      1     28      2    97%   134, 147->162
app\routers\users.py         94      1     30      1    98%   163
app\chemas\license.py        43      1      6      1    96%   44
app\services\audit.py        53      7      8      2    82%   42-44, 47, 108-110
--------------------------------------------------------------------
TOTAL                         1315     36    238     20    96%    29 files skipped due to complete coverage.
```

**Overall coverage: 96%** (target: ≥ 80%).

---

## 4. Static quality, security scanning and dependency audit

| Check | Command | Result |
|---|---|---|
| Ruff lint | `ruff check .` | **Pass** |
| Ruff format | `ruff format --check .` | **Pass** |
| Bandit (medium+) | `bandit -r app -ll` | **No issues identified** |
| pip-audit (runtime deps) | `pip-audit -r requirements.txt` | **No known vulnerabilities found** |
| Bandit (full, `app` only) | `bandit -r app` | **No High / Critical findings** |

---

## 5. Database migration validation

- Alembic migration `0001_initial` executed successfully against MySQL 8.4 (`alembic upgrade head`).
- Full test suite executed twice against a real MySQL database:

  1. Against a fresh SQLite file database.
  2. Against the Dockerized MySQL 8.4 instance via `TEST_DATABASE_URL`.

  Both runs: **132 passed**.

---

## 6. Test case status summary (from `04-test-plan.md`)

| Group | TC IDs | Pass | Fail | Blocked |
|---|---|---:|---:|---:|
| Authentication | TC-01 … TC-06 | 6 | 0 | 0 |
| Authorization / BOLA | TC-07 … TC-11 | 5 | 0 | 0 |
| Validation / injection | TC-12 … TC-17 | 6 | 0 | 0 |
| Functional | TC-18 … TC-23 | 6 | 0 | 0 |
| Errors / config / scans | TC-24 … TC-27 | 4 | 0 | 0 |
| **Total** | **TC-01 … TC-27** | **27** | **0** | **0** |

---

## 7. Manual security testing status

Manual testing (Burp Suite, SQLmap, curl, live Docker stack) is **pending** and will be
documented in this report as findings are executed and remediated.

---

## 8. Conclusion

- All 27 planned test cases (authentication, authorization, validation, functional, error handling and security scans) have automated counterparts that pass.
- The API maintains **96% branch coverage**, exceeding the 80% requirement.
- Bandit, pip-audit, Ruff and format checks pass with no High findings.
- Security headers, error handling, token validation and RBAC behaviours were verified by automated tests.

---

## 9. Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-11-20 | Mohamed Yossef | Initial test report |
