"""BOLA / IDOR tests for inspection ownership."""

from __future__ import annotations

from app.models import Inspection

from tests.factories import create_facility, create_inspection


def test_inspector_cannot_update_another_inspectors_inspection(client, auth, db, users) -> None:
    facility = create_facility(db)
    inspection = create_inspection(db, facility, users["inspector_b"])
    original_result = inspection.result

    response = client.put(
        f"/inspections/{inspection.id}",
        json={"result": "compliant", "notes": "Tampered"},
        headers=auth["inspector_a"],
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "You can only update your own inspections."

    db.expire_all()
    unchanged = db.get(Inspection, inspection.id)
    assert unchanged.result == original_result
    assert unchanged.notes is None

    audit = client.get(
        f"/audit-logs?action=access_denied&entity_id={inspection.id}",
        headers=auth["admin_test"],
    )
    assert audit.status_code == 200
    assert audit.json()["total"] == 1
    assert audit.json()["items"][0]["username"] == "inspector_a"
    assert audit.json()["items"][0]["details"] == "owner_check"


def test_owner_and_admin_can_update_inspection(client, auth, db, users) -> None:
    facility = create_facility(db)
    own = create_inspection(db, facility, users["inspector_a"])
    other = create_inspection(db, facility, users["inspector_b"])

    own_update = client.put(
        f"/inspections/{own.id}",
        json={"result": "partially_compliant"},
        headers=auth["inspector_a"],
    )
    assert own_update.status_code == 200

    admin_update = client.put(
        f"/inspections/{other.id}",
        json={"result": "follow_up_required"},
        headers=auth["admin_test"],
    )
    assert admin_update.status_code == 200


def test_inspector_cannot_create_inspection_on_behalf_of_another(client, auth, db, users) -> None:
    facility = create_facility(db)
    response = client.post(
        "/inspections",
        json={
            "facility_id": facility.id,
            "inspector_id": users["inspector_b"].id,
            "inspection_date": "2026-01-01",
            "result": "compliant",
        },
        headers=auth["inspector_a"],
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Inspectors can only record their own inspections."

    listing = client.get(f"/inspections?facility_id={facility.id}", headers=auth["admin_test"])
    assert listing.json()["total"] == 0


def test_inspection_owner_cannot_be_reassigned_via_mass_assignment(client, auth, db, users) -> None:
    facility = create_facility(db)
    inspection = create_inspection(db, facility, users["inspector_a"])
    response = client.put(
        f"/inspections/{inspection.id}",
        json={"inspector_id": users["inspector_b"].id},
        headers=auth["inspector_a"],
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "extra_forbidden"
