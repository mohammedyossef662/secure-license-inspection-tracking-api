"""Integration tests for inspections."""

from __future__ import annotations

from datetime import timedelta

from app.core.time import utc_today
from app.models import InspectionResult

from tests.factories import create_facility, create_inspection, create_user


def inspection_payload(facility_id: int, **overrides) -> dict:
    payload = {
        "facility_id": facility_id,
        "inspection_date": str(utc_today()),
        "result": "compliant",
        "notes": "Routine inspection.",
    }
    payload.update(overrides)
    return payload


def test_admin_records_inspection_for_an_inspector(client, auth, db, users) -> None:
    facility = create_facility(db)
    response = client.post(
        "/inspections",
        json=inspection_payload(facility.id, inspector_id=users["inspector_a"].id),
        headers=auth["admin_test"],
    )
    assert response.status_code == 201
    body = response.json()
    assert body["inspector_id"] == users["inspector_a"].id
    assert body["inspector_username"] == "inspector_a"


def test_inspector_records_own_inspection(client, auth, db, users) -> None:
    facility = create_facility(db)
    response = client.post(
        "/inspections",
        json=inspection_payload(facility.id),
        headers=auth["inspector_a"],
    )
    assert response.status_code == 201
    assert response.json()["inspector_id"] == users["inspector_a"].id

    explicit_self = client.post(
        "/inspections",
        json=inspection_payload(
            facility.id, inspector_id=users["inspector_a"].id, result="non_compliant"
        ),
        headers=auth["inspector_a"],
    )
    assert explicit_self.status_code == 201


def test_inspection_create_validation(client, auth, db, users, password_hash) -> None:
    facility = create_facility(db)
    assert (
        client.post(
            "/inspections",
            json=inspection_payload(999999),
            headers=auth["admin_test"],
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/inspections",
            json=inspection_payload(
                facility.id, inspection_date=str(utc_today() + timedelta(days=1))
            ),
            headers=auth["inspector_a"],
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/inspections",
            json=inspection_payload(facility.id, inspector_id=users["viewer_test"].id),
            headers=auth["admin_test"],
        ).status_code
        == 422
    )

    inactive = create_user(db, "inactive_inspector", "inspector", password_hash, is_active=False)
    assert (
        client.post(
            "/inspections",
            json=inspection_payload(facility.id, inspector_id=inactive.id),
            headers=auth["admin_test"],
        ).status_code
        == 422
    )


def test_inspection_list_filters(client, auth, db, users) -> None:
    facility_one = create_facility(db, "Facility One", "REG-500")
    facility_two = create_facility(db, "Facility Two", "REG-501")
    today = utc_today()
    first = create_inspection(
        db,
        facility_one,
        users["inspector_a"],
        today,
        InspectionResult.COMPLIANT,
    )
    second = create_inspection(
        db,
        facility_two,
        users["inspector_b"],
        today - timedelta(days=5),
        InspectionResult.NON_COMPLIANT,
    )

    by_facility = client.get(
        f"/inspections?facility_id={facility_one.id}", headers=auth["viewer_test"]
    )
    assert by_facility.status_code == 200
    assert by_facility.json()["total"] == 1
    assert by_facility.json()["items"][0]["id"] == first.id

    by_inspector = client.get(
        f"/inspections?inspector_id={users['inspector_b'].id}",
        headers=auth["viewer_test"],
    )
    assert by_inspector.json()["items"][0]["id"] == second.id

    by_result = client.get("/inspections?result=non_compliant", headers=auth["viewer_test"])
    assert by_result.json()["total"] == 1
    assert by_result.json()["items"][0]["id"] == second.id

    by_dates = client.get(
        f"/inspections?date_from={today - timedelta(days=1)}&date_to={today}",
        headers=auth["viewer_test"],
    )
    assert by_dates.json()["total"] == 1
    assert by_dates.json()["items"][0]["id"] == first.id

    invalid = client.get(
        f"/inspections?date_from={today}&date_to={today - timedelta(days=1)}",
        headers=auth["viewer_test"],
    )
    assert invalid.status_code == 422


def test_inspection_read_and_missing(client, auth, db, users) -> None:
    facility = create_facility(db)
    inspection = create_inspection(db, facility, users["inspector_a"])
    response = client.get(f"/inspections/{inspection.id}", headers=auth["viewer_test"])
    assert response.status_code == 200
    assert response.json()["inspector_username"] == "inspector_a"
    assert client.get("/inspections/999999", headers=auth["viewer_test"]).status_code == 404


def test_owner_updates_own_inspection_and_can_clear_notes(client, auth, db, users) -> None:
    facility = create_facility(db)
    inspection = create_inspection(db, facility, users["inspector_a"], notes="Original")
    response = client.put(
        f"/inspections/{inspection.id}",
        json={"result": "follow_up_required", "notes": None},
        headers=auth["inspector_a"],
    )
    assert response.status_code == 200
    assert response.json()["result"] == "follow_up_required"
    assert response.json()["notes"] is None

    empty = client.put(f"/inspections/{inspection.id}", json={}, headers=auth["inspector_a"])
    assert empty.status_code == 422
    missing = client.put(
        "/inspections/999999", json={"result": "compliant"}, headers=auth["inspector_a"]
    )
    assert missing.status_code == 404


def test_admin_updates_any_inspection(client, auth, db, users) -> None:
    facility = create_facility(db)
    inspection = create_inspection(db, facility, users["inspector_a"])
    response = client.put(
        f"/inspections/{inspection.id}",
        json={"inspection_date": str(utc_today() - timedelta(days=2))},
        headers=auth["admin_test"],
    )
    assert response.status_code == 200
    assert response.json()["inspection_date"] == str(utc_today() - timedelta(days=2))
