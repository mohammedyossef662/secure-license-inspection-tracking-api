# Threat Model

**Project:** Regulatory License & Inspection Tracking API
**Version:** 0.1
**Related documents:** `01-requirements.md`, `02-architecture.md`, `04-test-plan.md`

---

## 1. Scope and assumptions

- Threat model covers the HTTP API surface, the authentication layer, the data model and the infrastructure defaults.
- Assumed attacker capabilities: network-adjacent or internet-facing access to the API endpoint.
- Assumed defenders: the engineering team, CI security gates, monitoring and operational procedures.

## 2. Assets

| Asset | Impact if compromised |
|---|---|
| User credentials / password hashes | Account takeover |
| JWT signing key | Token forgery / privilege escalation |
| Facility / license / inspection data | Regulatory integrity loss |
| Audit log | Non-attributable actions |
| Admin account | Full data access |

## 3. Trust boundaries

1. Client → API (TLS assumed, auth header validated).
2. API → Database (internal network assumed).
3. Load balancer / reverse proxy → API (`X-Forwarded-*` only honoured when `TRUST_PROXY_HEADERS=true`).

## 4. Threats and mitigations (OWASP API Security Top 10 mapping)

| Risk | OWASP API ID | Mitigation implemented | Test coverage |
|---|---|---|---|
| Broken Object Level Authorization | API1:2023 | Object-ownership checks in update paths; inspector ownership enforced (BOLA tests) | TC-09, `tests/security/test_bola.py` |
| Broken Authentication | API2:2023 | Signed JWT with `iss/aud/exp/nbf/sub/jti`, short expiry, tampered-token rejection, rate limiting | TC-02…TC-06, `tests/security/test_tokens.py` |
| Broken Object Property Level Authorization | API3:2023 | Strict Pydantic models with `extra="forbid"` | TC-16, `tests/security/test_injection.py` |
| Unrestricted Resource Consumption | API4:2023 | Pagination limit 100, login rate limiting, query validation | TC-06, TC-21 |
| Broken Function Level Authorization | API5:2023 | Role-based dependencies per route | TC-07…TC-11, `tests/security/test_rbac.py` |
| Security Misconfiguration | API8:2023 | Security headers, CSP, HSTS, CORS allow-list, trusted host, docs disabled outside dev, generic errors | `tests/security/test_headers_and_errors.py` |
| Injection | API8:2023 / OWASP A03 | Parameterized ORM queries, escaped `LIKE` patterns, strict enum validation, no SQL echo | TC-15, `tests/security/test_injection.py` |
| Information disclosure / sensitive data exposure | OWASP A02 | Error responses generic, validation errors omit `input`/`ctx`, response models omit password hashes | TC-24, `tests/security/test_headers_and_errors.py` |
| Insufficient logging / monitoring | OWASP A09 | Audit log for logins, denials, mutations; login failures and access denials persisted | TC-22, `tests/integration/test_audit_logs.py` |
| Vulnerable dependencies / insecure design | OWASP A06 / A04 | CI: Bandit, pip-audit, Ruff, CodeQL default setup | TC-26, TC-27 |

## 5. Additional OWASP controls implemented

| Control | Requirement | Implementation | Verification |
|---|---|---|---|
| Token revocation | SR-14 / API2:2023 | `POST /auth/logout` blacklists the token `jti` until expiry | `tests/integration/test_auth.py` |
| Password complexity | SR-15 / A02:2023 | `_validate_password` (min 12 chars, upper + lower + digit + special) | `tests/unit/test_schemas.py` |
| Body size limit | SR-16 / API4:2023 | `RequestBodyLimitMiddleware` (64 KiB) | `tests/security/test_headers_and_errors.py` |

## 6. Residual risks

| Risk | Likelihood | Impact | Accepted mitigation |
|---|---|---|---|
| Rate limiting is per-process (not shared) | Medium | Low | Move to Redis-backed limiter for multi-instance deployments (documented in `02-architecture.md`) |
| Refresh tokens not implemented (access tokens only) | Medium | Medium | Short 15-minute access tokens limit exposure; refresh token support planned |

## 7. Security requirements mapping

See `01-requirements.md` §5 for the authoritative list (SR-01 … SR-13).

## 8. Review history

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-11-20 | Mohamed Yossef | Initial threat model |
