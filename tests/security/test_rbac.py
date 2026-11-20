"""RBAC and function-level authorization tests."""

from __future__ import annotations

import pytest

from tests.factories import create_facility, create_inspection, create_license


def test_viewer_cannot_perform_write_or_admin_actions(client, auth, db, users) -> None:
    facility = create_facility(db)
    license_obj = create_license(db, facility)
    inspection = create_inspection(db, facility, users["inspector_a"])
    headers = auth["viewer_test"]

    assert (
        client.post(
            "/facilities",
            json={
                "name": "Forbidden Facility",
                "registration_number": "REG-700",
                "address": "1 Forbidden Street",
            },
            headers=headers,
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"/facilities/{facility.id}", json={"name": "Hacked"}, headers=headers
        ).status_code
        == 403
    )
    assert client.delete(f"/facilities/{facility.id}", headers=headers).status_code == 403
    assert (
        client.post(
            "/licenses",
            json={
                "facility_id": facility.id,
                "license_number": "LIC-700",
                "type": "operating",
                "issue_date": "2026-01-01",
                "expiry_date": "2027-01-01",
            },
            headers=headers,
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"/licenses/{license_obj.id}",
            json={"status": "revoked"},
            headers=headers,
        ).status_code
        == 403
    )
    assert client.delete(f"/licenses/{license_obj.id}", headers=headers).status_code == 403
    assert (
        client.post(
            "/inspections",
            json={
                "facility_id": facility.id,
                "inspection_date": "2026-01-01",
                "result": "compliant",
            },
            headers=headers,
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"/inspections/{inspection.id}",
            json={"result": "non_compliant"},
            headers=headers,
        ).status_code
        == 403
    )
    assert client.get("/audit-logs", headers=headers).status_code == 403
    assert client.get("/users", headers=headers).status_code == 403
    assert (
        client.post(
            "/users",
            json={"username": "evil_user", "password": "EvilPassword_123!"},
            headers=headers,
        ).status_code
        == 403
    )


def test_inspector_cannot_perform_admin_actions(client, auth, db) -> None:
    facility = create_facility(db)
    license_obj = create_license(db, facility)
    headers = auth["inspector_a"]

    assert (
        client.post(
            "/facilities",
            json={
                "name": "Inspector Facility",
                "registration_number": "REG-701",
                "address": "1 Inspector Street",
            },
            headers=headers,
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"/facilities/{facility.id}", json={"name": "Changed"}, headers=headers
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/licenses",
            json={
                "facility_id": facility.id,
                "license_number": "LIC-701",
                "type": "operating",
                "issue_date": "2026-01-01",
                "expiry_date": "2027-01-01",
            },
            headers=headers,
        ).status_code
        == 403
    )
    assert client.delete(f"/licenses/{license_obj.id}", headers=headers).status_code == 403
    assert client.get("/audit-logs", headers=headers).status_code == 403
    assert client.get("/users", headers=headers).status_code == 403
    assert (
        client.post(
            "/users",
            json={"username": "inspector_made_user", "password": "Password_12345!"},
            headers=headers,
        ).status_code
        == 403
    )


@pytest.mark.parametrize(
    "path",
    ["/facilities", "/licenses", "/inspections", "/users", "/users/me", "/audit-logs"],
)
def test_protected_read_endpoints_require_authentication(client, path) -> None:
    response = client.get(path)
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated."


def test_authorization_denials_are_audited(client, auth) -> None:
    client.post(
        "/facilities",
        json={
            "name": "Denied Facility",
            "registration_number": "REG-702",
            "address": "1 Denied Street",
        },
        headers=auth["viewer_test"],
    )
    response = client.get("/audit-logs?action=access_denied", headers=auth["admin_test"])
    assert response.status_code == 200
    denied = response.json()["items"]
    assert denied
    assert denied[0]["username"] == "viewer_test"
    assert "path=/facilities" in denied[0]["details"]
