"""Integration tests for licenses."""

from __future__ import annotations

from datetime import timedelta

from app.core.time import utc_today
from app.models import LicenseStatus, LicenseType

from tests.factories import create_facility, create_license


def license_payload(facility_id: int, **overrides) -> dict:
    today = utc_today()
    payload = {
        "facility_id": facility_id,
        "license_number": "lic-100",
        "type": "operating",
        "issue_date": str(today - timedelta(days=30)),
        "expiry_date": str(today + timedelta(days=365)),
        "status": "active",
    }
    payload.update(overrides)
    return payload


def test_admin_creates_license(client, auth, db) -> None:
    facility = create_facility(db)
    response = client.post(
        "/licenses", json=license_payload(facility.id), headers=auth["admin_test"]
    )
    assert response.status_code == 201
    body = response.json()
    assert body["license_number"] == "LIC-100"
    assert body["facility_id"] == facility.id
    assert body["is_expired"] is False


def test_license_create_rejects_missing_facility_and_duplicate(client, auth, db) -> None:
    missing = client.post("/licenses", json=license_payload(999999), headers=auth["admin_test"])
    assert missing.status_code == 404

    facility = create_facility(db)
    assert (
        client.post(
            "/licenses", json=license_payload(facility.id), headers=auth["admin_test"]
        ).status_code
        == 201
    )
    duplicate = client.post(
        "/licenses", json=license_payload(facility.id), headers=auth["admin_test"]
    )
    assert duplicate.status_code == 409


def test_license_dates_are_validated(client, auth, db) -> None:
    facility = create_facility(db)
    today = utc_today()
    response = client.post(
        "/licenses",
        json=license_payload(
            facility.id,
            issue_date=str(today),
            expiry_date=str(today),
        ),
        headers=auth["admin_test"],
    )
    assert response.status_code == 422


def test_license_list_filters_and_expiry_flag(client, auth, db) -> None:
    facility = create_facility(db)
    active = create_license(db, facility, "LIC-201", LicenseType.OPERATING)
    expired = create_license(
        db,
        facility,
        "LIC-202",
        LicenseType.RADIATION,
        issue_date=utc_today() - timedelta(days=400),
        expiry_date=utc_today() - timedelta(days=10),
    )
    revoked = create_license(
        db,
        facility,
        "LIC-203",
        LicenseType.TRANSPORT,
        status=LicenseStatus.REVOKED,
    )

    all_licenses = client.get("/licenses", headers=auth["viewer_test"])
    assert all_licenses.status_code == 200
    assert all_licenses.json()["total"] == 3

    by_type = client.get("/licenses?type=radiation", headers=auth["viewer_test"])
    assert by_type.json()["total"] == 1
    assert by_type.json()["items"][0]["id"] == expired.id

    only_expired = client.get("/licenses?expired=true", headers=auth["viewer_test"])
    assert only_expired.json()["total"] == 1
    assert only_expired.json()["items"][0]["is_expired"] is True

    only_valid = client.get("/licenses?expired=false", headers=auth["viewer_test"])
    assert only_valid.json()["total"] == 2

    by_status = client.get("/licenses?status=revoked", headers=auth["viewer_test"])
    assert by_status.json()["total"] == 1
    assert by_status.json()["items"][0]["id"] == revoked.id

    by_facility = client.get(f"/licenses?facility_id={facility.id}", headers=auth["viewer_test"])
    assert by_facility.json()["total"] == 3

    search = client.get("/licenses?search=LIC-202", headers=auth["viewer_test"])
    assert search.json()["total"] == 1
    assert search.json()["items"][0]["id"] == expired.id
    assert active.id != expired.id


def test_license_read_and_missing(client, auth, db) -> None:
    facility = create_facility(db)
    license_obj = create_license(db, facility)
    response = client.get(f"/licenses/{license_obj.id}", headers=auth["viewer_test"])
    assert response.status_code == 200
    assert client.get("/licenses/999999", headers=auth["viewer_test"]).status_code == 404


def test_admin_updates_license_dates_status_and_number(client, auth, db) -> None:
    facility = create_facility(db)
    license_obj = create_license(db, facility, "LIC-300")
    today = utc_today()

    invalid = client.put(
        f"/licenses/{license_obj.id}",
        json={"expiry_date": str(today - timedelta(days=40))},
        headers=auth["admin_test"],
    )
    assert invalid.status_code == 422

    updated = client.put(
        f"/licenses/{license_obj.id}",
        json={
            "license_number": "LIC-301",
            "status": "revoked",
            "expiry_date": str(today + timedelta(days=700)),
        },
        headers=auth["admin_test"],
    )
    assert updated.status_code == 200
    assert updated.json()["license_number"] == "LIC-301"
    assert updated.json()["status"] == "revoked"

    empty = client.put(f"/licenses/{license_obj.id}", json={}, headers=auth["admin_test"])
    assert empty.status_code == 422
    assert (
        client.put(
            "/licenses/999999", json={"status": "revoked"}, headers=auth["admin_test"]
        ).status_code
        == 404
    )


def test_duplicate_license_number_on_update(client, auth, db) -> None:
    facility = create_facility(db)
    first = create_license(db, facility, "LIC-400")
    second = create_license(db, facility, "LIC-401")
    duplicate = client.put(
        f"/licenses/{second.id}",
        json={"license_number": first.license_number},
        headers=auth["admin_test"],
    )
    assert duplicate.status_code == 409


def test_delete_license_removes_it_from_reads(client, auth, db) -> None:
    facility = create_facility(db)
    license_obj = create_license(db, facility)
    response = client.delete(f"/licenses/{license_obj.id}", headers=auth["admin_test"])
    assert response.status_code == 204
    assert client.get(f"/licenses/{license_obj.id}", headers=auth["admin_test"]).status_code == 404
    assert client.delete("/licenses/999999", headers=auth["admin_test"]).status_code == 404


def test_license_cannot_be_created_for_deleted_facility(client, auth, db) -> None:
    facility = create_facility(db)
    facility.is_deleted = True
    db.commit()
    response = client.post(
        "/licenses", json=license_payload(facility.id), headers=auth["admin_test"]
    )
    assert response.status_code == 404
