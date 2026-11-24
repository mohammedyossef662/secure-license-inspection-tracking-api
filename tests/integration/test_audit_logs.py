"""Integration tests for the audit log endpoint."""

from __future__ import annotations

from datetime import timedelta

from app.core.time import utcnow

from tests.factories import create_facility


def test_audit_log_is_populated_by_actions(client, auth, db, users) -> None:
    facility = create_facility(db, "Audited Facility", "REG-600")
    create = client.post(
        "/facilities",
        json={
            "name": "Second Audited Facility",
            "registration_number": "REG-601",
            "address": "1 Audit Street, Cairo",
        },
        headers=auth["admin_test"],
    )
    assert create.status_code == 201

    response = client.get("/audit-logs", headers=auth["admin_test"])
    assert response.status_code == 200
    body = response.json()
    assert body["total"] > 0
    assert all("username" in item for item in body["items"])

    filtered = client.get("/audit-logs?action=facility_created", headers=auth["admin_test"])
    assert filtered.status_code == 200
    assert filtered.json()["total"] >= 1
    assert filtered.json()["items"][0]["entity"] == "facility"
    assert filtered.json()["items"][0]["username"] == "admin_test"

    by_entity = client.get(
        f"/audit-logs?entity=facility&entity_id={facility.id}",
        headers=auth["admin_test"],
    )
    assert by_entity.status_code == 200
    assert by_entity.json()["total"] == 0

    by_user = client.get(
        f"/audit-logs?user_id={users['admin_test'].id}", headers=auth["admin_test"]
    )
    assert by_user.status_code == 200
    assert by_user.json()["total"] >= 1


def test_audit_log_date_filter_and_pagination(client, auth) -> None:
    today = utcnow()
    date_from = (today - timedelta(days=1)).isoformat()
    date_to = (today + timedelta(days=1)).isoformat()

    filtered = client.get(
        f"/audit-logs?date_from={date_from}&date_to={date_to}",
        headers=auth["admin_test"],
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] >= 1

    page = client.get("/audit-logs?page=1&size=2", headers=auth["admin_test"])
    assert page.status_code == 200
    assert len(page.json()["items"]) <= 2
    assert page.json()["size"] == 2

    invalid_range = client.get(
        f"/audit-logs?date_from={date_to}&date_to={date_from}",
        headers=auth["admin_test"],
    )
    assert invalid_range.status_code == 422

    invalid_action = client.get("/audit-logs?action=not_a_real_action", headers=auth["admin_test"])
    assert invalid_action.status_code == 422

    too_long_entity = client.get("/audit-logs?entity=" + "x" * 33, headers=auth["admin_test"])
    assert too_long_entity.status_code == 422
