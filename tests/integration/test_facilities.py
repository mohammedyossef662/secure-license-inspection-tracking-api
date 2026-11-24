"""Integration tests for facilities."""

from __future__ import annotations

from datetime import timedelta

from app.core.time import utc_today
from app.models import FacilityStatus

from tests.factories import create_facility, create_license


def facility_payload(**overrides) -> dict:
    payload = {
        "name": "Nile Chemicals",
        "registration_number": "reg-100",
        "address": "15 Industrial Zone, Cairo",
        "status": "active",
    }
    payload.update(overrides)
    return payload


def test_admin_creates_facility_and_audit_entry(client, auth) -> None:
    response = client.post("/facilities", json=facility_payload(), headers=auth["admin_test"])
    assert response.status_code == 201
    body = response.json()
    assert body["registration_number"] == "REG-100"
    assert body["status"] == "active"

    audit = client.get(
        f"/audit-logs?action=facility_created&entity_id={body['id']}",
        headers=auth["admin_test"],
    )
    assert audit.status_code == 200
    assert audit.json()["total"] == 1
    assert audit.json()["items"][0]["user_id"] is not None


def test_duplicate_registration_number_is_rejected(client, auth) -> None:
    assert (
        client.post("/facilities", json=facility_payload(), headers=auth["admin_test"]).status_code
        == 201
    )
    duplicate = client.post(
        "/facilities",
        json=facility_payload(name="Other Name"),
        headers=auth["admin_test"],
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Registration number is already in use."


def test_facility_list_search_filter_and_pagination(client, auth, db) -> None:
    create_facility(db, "Acme Materials", "REG-201")
    create_facility(db, "Acme Logistics", "REG-202")
    create_facility(
        db,
        "Beta Radiation",
        "REG-203",
        status=FacilityStatus.SUSPENDED,
    )

    search = client.get("/facilities?search=Acme", headers=auth["viewer_test"])
    assert search.status_code == 200
    assert search.json()["total"] == 2

    filtered = client.get("/facilities?status=suspended", headers=auth["viewer_test"])
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["name"] == "Beta Radiation"

    page = client.get("/facilities?page=1&size=2", headers=auth["inspector_a"])
    assert page.status_code == 200
    assert len(page.json()["items"]) == 2
    assert page.json()["pages"] == 2
    assert page.json()["total"] == 3


def test_facility_read_and_missing(client, auth, db) -> None:
    facility = create_facility(db, "Readable Facility", "REG-210")
    response = client.get(f"/facilities/{facility.id}", headers=auth["viewer_test"])
    assert response.status_code == 200
    assert response.json()["registration_number"] == "REG-210"
    assert client.get("/facilities/999999", headers=auth["viewer_test"]).status_code == 404


def test_admin_updates_facility_and_duplicate_check(client, auth, db) -> None:
    first = create_facility(db, "First", "REG-220")
    second = create_facility(db, "Second", "REG-221")

    updated = client.put(
        f"/facilities/{first.id}",
        json={"name": "First Renamed", "status": "suspended"},
        headers=auth["admin_test"],
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "First Renamed"
    assert updated.json()["status"] == "suspended"

    duplicate = client.put(
        f"/facilities/{second.id}",
        json={"registration_number": "REG-220"},
        headers=auth["admin_test"],
    )
    assert duplicate.status_code == 409

    empty = client.put(f"/facilities/{first.id}", json={}, headers=auth["admin_test"])
    assert empty.status_code == 422

    explicit_null = client.put(
        f"/facilities/{first.id}",
        json={"name": None},
        headers=auth["admin_test"],
    )
    assert explicit_null.status_code == 422
    missing = client.put("/facilities/999999", json={"name": "X Y"}, headers=auth["admin_test"])
    assert missing.status_code == 404


def test_delete_facility_with_active_license_is_rejected(client, auth, db) -> None:
    facility = create_facility(db, "Licensed Facility", "REG-230")
    create_license(db, facility)
    response = client.delete(f"/facilities/{facility.id}", headers=auth["admin_test"])
    assert response.status_code == 409
    assert response.json()["detail"] == "Facility has active licenses and cannot be deleted."


def test_delete_facility_with_expired_license_soft_deletes_everything(client, auth, db) -> None:
    facility = create_facility(db, "Closing Facility", "REG-240")
    today = utc_today()
    create_license(
        db,
        facility,
        issue_date=today - timedelta(days=400),
        expiry_date=today - timedelta(days=1),
    )
    response = client.delete(f"/facilities/{facility.id}", headers=auth["admin_test"])
    assert response.status_code == 204

    assert client.get(f"/facilities/{facility.id}", headers=auth["admin_test"]).status_code == 404
    licensed = client.get(f"/licenses?facility_id={facility.id}", headers=auth["admin_test"])
    assert licensed.status_code == 200
    assert licensed.json()["total"] == 0

    audit = client.get(
        f"/audit-logs?action=facility_deleted&entity_id={facility.id}",
        headers=auth["admin_test"],
    )
    assert audit.status_code == 200
    assert audit.json()["items"][0]["details"] == "cascaded_licenses=1"


def test_facility_validation_and_missing_delete(client, auth) -> None:
    too_long = client.post(
        "/facilities",
        json=facility_payload(name="N" * 10_000),
        headers=auth["admin_test"],
    )
    assert too_long.status_code == 422
    assert "input" not in too_long.text

    missing = client.delete("/facilities/999999", headers=auth["admin_test"])
    assert missing.status_code == 404
