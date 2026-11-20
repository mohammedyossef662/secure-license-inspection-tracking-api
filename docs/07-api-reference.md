# API Reference

**Project:** Regulatory License & Inspection Tracking API
**Version:** 0.1

Base URL: `/` (e.g. `http://localhost:8000`)

---

## 1. Conventions

- **Auth:** `Authorization: Bearer <access_token>` (OAuth2, token URL `/auth/login`).
- **Errors:** JSON body `{ "detail": ... }`; validation errors: `{ "detail": [ { "loc", "msg", "type" } ] }`.
- **Success list payload:** `{ "items": [...], "total": int, "page": int, "size": int, "pages": int }`.
- **Dates:** ISO 8601 (`YYYY-MM-DD`); timestamps are naive UTC.
- **IDs:** integers.

---

## 2. Operations

### `GET /health`

Public. Returns `200 {status, database, version}` or `503 {status: degraded, database: unavailable, version}`.

---

## 3. Authentication

### `POST /auth/login`

**Auth:** none.

Request (JSON):

```json
{ "username": "admin", "password": "AdminPassword_123!" }
```

OAuth2 form (`application/x-www-form-urlencoded`) is also accepted.

Responses:

- `200`: `{ access_token, token_type, expires_in, user }`
- `401`: `{ "detail": "Invalid username or password." }`
- `422`: validation error (no value echo)
- `429`: `{ "detail": "Too many login attempts. Try again later." }` with `Retry-After`

### `POST /auth/logout`

**Auth:** Bearer.

Blacklists the presented access token until its original expiry.

Responses:

- `204`: token revoked
- `401`: token missing/invalid/revoked

---

## 4. Users

All user endpoints except `GET/PUT /users/me` require Admin (`AdminUser`).

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/users/me` | Bearer | Current user |
| PUT | `/users/me` | Bearer | Update profile / change password (current password required) |
| POST | `/users` | Admin | Create user |
| GET | `/users` | Admin | Paginated, filterable (`role`, `is_active`, `search`) user list |
| GET | `/users/{user_id}` | Admin | Read user |
| PUT | `/users/{user_id}` | Admin | Update user |
| DELETE | `/users/{user_id}` | Admin | Deactivate user (self-deactivation blocked) |

---

## 5. Facilities

| Method | Path | Auth | RBAC | Description |
|---|---|---|---|---|
| GET | `/facilities` | Bearer | All | List; filters `search`, `status`; pagination |
| POST | `/facilities` | Admin | Admin | Create |
| GET | `/facilities/{facility_id}` | Bearer | All | Read |
| PUT | `/facilities/{facility_id}` | Admin | Admin | Update |
| DELETE | `/facilities/{facility_id}` | Admin | Admin | Soft delete; blocked when an active (non-expired) license exists |

---

## 6. Licenses

| Method | Path | Auth | RBAC | Description |
|---|---|---|---|---|
| GET | `/licenses` | Bearer | All | List; filters `facility_id`, `status`, `type`, `expired`, `search`; pagination |
| POST | `/licenses` | Admin | Admin | Create; `expiry_date` must be after `issue_date` |
| GET | `/licenses/{license_id}` | Bearer | All | Read |
| PUT | `/licenses/{license_id}` | Admin | Admin | Update |
| DELETE | `/licenses/{license_id}` | Admin | Admin | Soft delete / revoke |

`LicenseRead` includes `is_expired` (expiry date passed).

---

## 7. Inspections

| Method | Path | Auth | RBAC | Description |
|---|---|---|---|---|
| GET | `/inspections` | Bearer | All | List; filters `facility_id`, `inspector_id`, `result`, `date_from`, `date_to`; pagination |
| POST | `/inspections` | Bearer | Admin / Inspector | Create; inspectors may only target themselves |
| GET | `/inspections/{inspection_id}` | Bearer | All | Read |
| PUT | `/inspections/{inspection_id}` | Bearer | Admin / Inspector | Update; inspectors only their own (BOLA) |

---

## 8. Audit logs

### `GET /audit-logs`

Admin only.

Filters: `action`, `entity`, `entity_id`, `user_id`, `date_from`, `date_to`; pagination.

---

## 9. Error codes

| Status | Meaning |
|---:|---|
| 400 | Bad request |
| 401 | Unauthorized (missing/invalid/expired token) |
| 403 | Forbidden (insufficient role / ownership) |
| 404 | Not found |
| 405 | Method not allowed |
| 409 | Conflict (duplicate / state conflict) |
| 422 | Validation error |
| 429 | Rate limited |
| 500 | Generic internal error |

---

## 10. OpenAPI

- `GET /docs`, `GET /redoc`, `GET /openapi.json` (disabled when `DOCS_ENABLED=false`).

---

## 11. Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-11-20 | Mohamed Yossef | Initial API reference |
