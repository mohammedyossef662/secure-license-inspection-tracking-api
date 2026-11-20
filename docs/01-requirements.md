# Requirements Specification

**Project:** Regulatory License & Inspection Tracking API
**Version:** 0.1 (Draft)
**Author:** Mohamed Yossef Mohamed
**Date:** 2026-11-20
**Status:** Draft / In Review / Approved

---

## 1. Introduction

### 1.1 Purpose

This document defines the functional, non-functional and security requirements for the License & Inspection Tracking API. It is the reference for design, development and testing.

### 1.2 Scope

**In scope:**

- Management of facilities, licenses and inspections
- User authentication and role-based authorization
- Audit logging of significant actions
- REST API with documentation

**Out of scope:**

- Front-end user interface
- Integration with real external systems
- Payment or billing
- Email/SMS notifications

### 1.3 Definitions

| Term | Meaning |
|---|---|
| Facility | An organization or site that holds a license |
| License | An authorization issued to a facility, with a validity period |
| Inspection | A recorded visit evaluating a facility's compliance |
| RBAC | Role-Based Access Control |
| BOLA | Broken Object Level Authorization |

### 1.4 References

- OWASP Top 10
- OWASP API Security Top 10
- OWASP ASVS (selected controls)

---

## 2. Overall Description

### 2.1 Users and Roles

| Role | Description |
|---|---|
| Admin | Full access, manages users, facilities, licenses |
| Inspector | Records and updates their own inspections, reads facilities and licenses |
| Viewer | Read-only access to facilities and licenses |

### 2.2 Assumptions and Constraints

- The API is consumed by trusted client applications over HTTPS.
- MySQL 8 is the only supported database.
- All data in this project is fictional.
- Local development uses SQLite for fast iteration; production uses MySQL 8.

### 2.3 Operating Environment

Python 3.12, MySQL 8, Docker, Linux-based deployment.

---

## 3. Functional Requirements

Priority: **M** = Must, **S** = Should, **C** = Could

| ID | Requirement | Priority | Role |
|---|---|---:|---|
| FR-01 | The system shall allow users to log in with a username and password and receive an access token. | M | All |
| FR-02 | The system shall allow an Admin to create, update and deactivate user accounts. | M | Admin |
| FR-03 | The system shall allow an Admin to create, read, update and delete facilities. | M | Admin |
| FR-04 | The system shall allow all authenticated users to list and view facilities. | M | All |
| FR-05 | The system shall allow an Admin to create, update and revoke licenses linked to a facility. | M | Admin |
| FR-06 | The system shall allow all authenticated users to list and view licenses. | M | All |
| FR-07 | The system shall allow Admins and Inspectors to record inspections for a facility. | M | Admin, Inspector |
| FR-08 | The system shall allow an Inspector to update only inspections they created. | M | Inspector |
| FR-09 | The system shall support filtering and pagination on list endpoints. | S | All |
| FR-10 | The system shall record an audit log entry for login attempts and all create, update and delete actions. | M | System |
| FR-11 | The system shall allow an Admin to view the audit log. | M | Admin |
| FR-12 | The system shall flag licenses that are past their expiry date. | C | System |

---

## 4. Non-Functional Requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-01 | Performance | Typical read requests shall respond in under 500 ms with a dataset of up to 10,000 records. |
| NFR-02 | Reliability | The API shall return consistent error formats and appropriate HTTP status codes. |
| NFR-03 | Maintainability | Code shall pass linting and maintain at least 80% test coverage. |
| NFR-04 | Portability | The system shall run via Docker Compose with a single command. |
| NFR-05 | Documentation | The API shall expose OpenAPI documentation, and all project documents shall be kept in the repository. |
| NFR-06 | Traceability | Every change to data shall be attributable to a user and timestamp. |
| NFR-07 | Data integrity | The database shall enforce foreign keys, unique constraints and NOT NULL rules. |

---

## 5. Security Requirements

| ID | Requirement | Reference |
|---|---|---|
| SR-01 | Passwords shall be stored only as salted hashes using Argon2 or bcrypt. | OWASP A02 |
| SR-02 | Access tokens shall be signed, expire within 15 minutes, and be rejected if tampered with or expired. | OWASP A07 |
| SR-03 | Every endpoint except login shall require authentication. | API2:2023 |
| SR-04 | Access shall be enforced by role on every endpoint (RBAC). | API5:2023 |
| SR-05 | The system shall verify object ownership before allowing modification (BOLA prevention). | API1:2023 |
| SR-06 | All input shall be validated for type, length, format and allowed values before processing. | OWASP A03 |
| SR-07 | Database access shall use parameterized queries via the ORM only. | OWASP A03 |
| SR-08 | Secrets (keys, database credentials) shall be supplied via environment variables and never committed. | OWASP A05 |
| SR-09 | Error responses shall not reveal stack traces, SQL errors or internal paths. | OWASP A05 |
| SR-10 | Login attempts shall be rate limited to reduce brute-force risk. | API4:2023 |
| SR-11 | Dependencies shall be scanned for known vulnerabilities in CI. | OWASP A06 |
| SR-12 | Source code shall be scanned by SAST tools in CI on every push. | OWASP A04 |
| SR-13 | Security-relevant events (login success/failure, permission denials, data changes) shall be logged. | OWASP A09 |
| SR-14 | Access tokens shall support explicit revocation (logout) until their original expiry. | OWASP API2:2023 |
| SR-15 | Passwords shall satisfy a complexity policy (minimum length plus upper, lower, digit and special characters). | OWASP A02:2023 |
| SR-16 | Request bodies shall be limited in size to mitigate large-payload abuse. | OWASP API4:2023 |

---

## 6. Data Requirements

### 6.1 Entities

| Entity | Key attributes |
|---|---|
| users | id, username (unique), password_hash, role, is_active, created_at |
| facilities | id, name, registration_number (unique), address, status, created_at |
| licenses | id, facility_id (FK), license_number (unique), type, issue_date, expiry_date, status |
| inspections | id, facility_id (FK), inspector_id (FK), inspection_date, result, notes |
| audit_logs | id, user_id, action, entity, entity_id, timestamp, ip_address |

### 6.2 Data rules

- Expiry date must be after issue date.
- Inspection date cannot be in the future.
- Deleting a facility with active licenses is not allowed.

---

## 7. Interface Requirements

- **API style:** REST over HTTPS, JSON request and response bodies.
- **Authentication header:** `Authorization: Bearer <token>`
- **Error format:** `{ "detail": "<message>" }` with correct HTTP status codes (400, 401, 403, 404, 422, 429, 500).
- **Documentation:** OpenAPI at `/docs` and `/openapi.json`.

---

## 8. Requirements Traceability

| Requirement | Design doc section | Test case(s) |
|---|---|---|
| FR-01 | 02-architecture §Auth | TC-01, TC-02 |
| FR-08 | 02-architecture §Authorization | TC-08, TC-09 |
| SR-05 | 03-threat-model | TC-09 |
| SR-06 | 02-architecture §Validation | TC-12, TC-13 |
| FR-03 / FR-05 / FR-09 / FR-10 / SR-02 / SR-03 / SR-04 / SR-06 / SR-07 / SR-08 / SR-09 / SR-10 / SR-11 / SR-12 / NFR-07 | — | see `04-test-plan.md` traceability matrix |

---

## 9. Open Questions

| # | Question | Owner | Status |
|---|---|---|---|
| 1 | [Question] | [Name] | Open |

---

## 10. Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-11-20 | Mohamed Yossef | Initial draft |

---
