# Test Plan

**Project:** Regulatory License & Inspection Tracking API
**Version:** 0.1 (Draft)
**Author:** Mohamed Yossef Mohamed
**Date:** 2026-11-20

---

## 1. Introduction

### 1.1 Purpose

This plan describes how the API will be tested to verify that it meets the functional, non-functional and security requirements in `01-requirements.md`.

### 1.2 Objectives

- Verify all Must-priority functional requirements.
- Verify authentication and authorization controls, including object-level access.
- Verify input validation and resistance to common injection attacks.
- Detect and document vulnerabilities, and verify their remediation.

---

## 2. Scope

### 2.1 In scope

- All REST endpoints
- Authentication, RBAC, ownership checks
- Input validation and error handling
- Database constraints and audit logging
- CI pipeline checks

### 2.2 Out of scope

- Front-end testing
- Load and stress testing beyond basic response-time checks
- Third-party infrastructure

---

## 3. Test Strategy

| Test type | Goal | Tools | Location |
|---|---|---|---|
| Unit | Verify functions and validators in isolation | pytest | `tests/unit/` |
| Integration | Verify endpoints with a real test database | pytest, httpx | `tests/integration/` |
| Security (automated) | Verify access control and injection handling | pytest | `tests/security/` |
| SAST | Find insecure code patterns | Bandit, CodeQL | CI |
| Dependency scan | Find vulnerable packages | pip-audit | CI |
| Manual security testing | Probe the running API like an attacker | Burp Suite, SQLmap, ffuf | Local Docker |
| Static quality | Enforce code standards | Ruff | CI |

---

## 4. Test Environment

| Item | Detail |
|---|---|
| OS | Ubuntu (CI) / Kali Linux (manual testing) |
| Python | 3.12 |
| Database | MySQL 8 (Docker container, test schema) |
| Test data | Fictional seed data created by fixtures |
| Test accounts | `admin_test`, `inspector_a`, `inspector_b`, `viewer_test` |

---

## 5. Entry and Exit Criteria

### Entry criteria

- Requirements document approved
- Application runs via Docker Compose
- Test database and seed data available

### Exit criteria

- All Must-priority test cases pass
- Code coverage at least 80%
- Zero High or Critical findings open from Bandit, CodeQL and pip-audit
- All manual security findings documented, with fixes verified
- Test report completed

---

## 6. Test Cases

Status values: Not Run / Pass / Fail / Blocked

### 6.1 Authentication

| ID | Req | Description | Steps | Expected result | Status |
|---|---|---|---|---|---|
| TC-01 | FR-01 | Login with valid credentials | POST `/auth/login` with valid user | 200, token returned | **Pass** |
| TC-02 | FR-01 | Login with wrong password | POST `/auth/login` with wrong password | 401, generic message | **Pass** |
| TC-03 | SR-03 | Access endpoint without token | GET `/facilities` with no header | 401 | **Pass** |
| TC-04 | SR-02 | Access with expired token | Use token past expiry | 401 | **Pass** |
| TC-05 | SR-02 | Access with tampered token | Modify token payload | 401 | **Pass** |
| TC-06 | SR-10 | Brute-force login | Send repeated failed logins rapidly | 429 after threshold | **Pass** |

### 6.2 Authorization (RBAC and BOLA)

| ID | Req | Description | Steps | Expected result | Status |
|---|---|---|---|---|---|
| TC-07 | SR-04 | Viewer attempts to create facility | POST `/facilities` as viewer | 403 | **Pass** |
| TC-08 | FR-08 | Inspector updates own inspection | PUT `/inspections/{own_id}` as inspector_a | 200 | **Pass** |
| TC-09 | SR-05 | Inspector updates another inspector's inspection | PUT `/inspections/{b_id}` as inspector_a | 403 or 404 | **Pass** |
| TC-10 | SR-04 | Non-admin views audit log | GET `/audit-logs` as inspector | 403 | **Pass** |
| TC-11 | SR-04 | Non-admin creates user | POST `/users` as viewer | 403 | **Pass** |

### 6.3 Input Validation and Injection

| ID | Req | Description | Steps | Expected result | Status |
|---|---|---|---|---|---|
| TC-12 | SR-06 | Invalid data type | Send string where integer expected | 422 | **Pass** |
| TC-13 | SR-06 | Field exceeds max length | Send 10,000-character name | 422 | **Pass** |
| TC-14 | SR-06 | Invalid date logic | `expiry_date` before `issue_date` | 422 | **Pass** |
| TC-15 | SR-07 | SQL injection in search parameter | `?name=' OR '1'='1` | No data leak, no DB error exposed | **Pass** |
| TC-16 | SR-06 | Mass assignment attempt | Send `"role": "admin"` in a profile update | Field ignored or rejected | **Pass** |
| TC-17 | SR-06 | Missing required fields | POST with empty body | 422 | **Pass** |

### 6.4 Functional

| ID | Req | Description | Steps | Expected result | Status |
|---|---|---|---|---|---|
| TC-18 | FR-03 | Admin creates facility | POST `/facilities` valid data | 201 | **Pass** |
| TC-19 | FR-03 | Duplicate registration number | POST same registration number twice | 409 or 422 | **Pass** |
| TC-20 | FR-05 | Admin creates license | POST `/licenses` valid data | 201 | **Pass** |
| TC-21 | FR-09 | Pagination | GET `/facilities?page=2&size=10` | Correct page returned | **Pass** |
| TC-22 | FR-10 | Audit log on create | Create facility then read audit log | Entry exists with user and timestamp | **Pass** |
| TC-23 | NFR-07 | Delete facility with active license | DELETE `/facilities/{id}` | Rejected | **Pass** |

### 6.5 Error Handling and Configuration

| ID | Req | Description | Steps | Expected result | Status |
|---|---|---|---|---|---|
| TC-24 | SR-09 | Trigger server error | Cause an unhandled exception | 500 with generic message, no stack trace | **Pass** |
| TC-25 | SR-08 | Secrets in repository | Scan repo history for secrets | None found | **Pass** (via `.gitignore` + scan) |
| TC-26 | SR-11 | Vulnerable dependency check | Run pip-audit | No High/Critical findings | **Pass** |
| TC-27 | SR-12 | SAST scan | Run Bandit and CodeQL | No High findings | **Pass** |

---

## 7. Manual Security Testing Plan

Performed against the running Docker environment, mapped to the OWASP API Security Top 10.

| OWASP API risk | Test approach | Tool |
|---|---|---|
| API1 Broken Object Level Authorization | Swap object IDs between users | Burp Repeater |
| API2 Broken Authentication | Token tampering, weak login protections | Burp, jwt tools |
| API3 Broken Object Property Level Authorization | Mass assignment, excessive data exposure | Burp |
| API4 Unrestricted Resource Consumption | Rate limit and pagination limit checks | ffuf, Burp Intruder |
| API5 Broken Function Level Authorization | Call admin endpoints as lower roles | Burp |
| API8 Security Misconfiguration | Headers, CORS, verbose errors | Burp, curl |
| Injection | SQL injection on all string parameters | SQLmap, manual |

Each finding is recorded in `05-test-report.md` with: description, severity, evidence, remediation and retest result.

---

## 8. Requirements Traceability Matrix

| Requirement | Test cases |
|---|---|
| FR-01 | TC-01, TC-02 |
| FR-03 | TC-18, TC-19 |
| FR-05 | TC-20 |
| FR-08 | TC-08, TC-09 |
| FR-09 | TC-21 |
| FR-10 | TC-22 |
| SR-02 | TC-04, TC-05 |
| SR-03 | TC-03 |
| SR-04 | TC-07, TC-10, TC-11 |
| SR-05 | TC-09 |
| SR-06 | TC-12, TC-13, TC-14, TC-16, TC-17 |
| SR-07 | TC-15 |
| SR-08 | TC-25 |
| SR-09 | TC-24 |
| SR-10 | TC-06 |
| SR-11 | TC-26 |
| SR-12 | TC-27 |
| NFR-07 | TC-23 |

---

## 9. Defect Management

| Severity | Definition | Action |
|---|---|---|
| Critical | Authentication bypass, data exposure, injection | Fix before any release |
| High | Authorization flaws, significant validation gaps | Fix before release |
| Medium | Limited-impact weaknesses | Fix in the next iteration |
| Low | Minor issues, hardening suggestions | Track in backlog |

Defects are tracked as GitHub Issues with the label `bug` or `security`.

---

## 10. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Test data differs from realistic data | Missed edge cases | Add varied seed data |
| CI database slower than local | Flaky tests | Use health checks and retries |
| Limited time for manual testing | Reduced coverage | Prioritize API1, API2, API5 and injection |

---

## 11. Schedule

| Week | Activity |
|---|---|
| 3 | Write automated tests and configure CI |
| 4 | Manual security testing, remediation, retest, test report |

---

## 12. Deliverables

- This test plan
- Automated test suite in `tests/`
- CI workflow results
- Test report: `05-test-report.md`

---

## 13. Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-11-20 | Mohamed Yossef | Initial draft |
