"""SQL injection, wildcard abuse and mass-assignment tests."""

from __future__ import annotations

from tests.factories import create_facility, create_license

INJECTION = "' OR '1'='1"


def _assert_no_internal_leak(response) -> None:
    lowered = response.text.lower()
    for marker in ("traceback", "sqlalchemy", "syntax error", "pymysql", "stack trace"):
        assert marker not in lowered


def test_sql_injection_in_facility_search_returns_no_data(client, auth, db) -> None:
    create_facility(db, "Acme Materials", "REG-800")
    response = client.get("/facilities", params={"search": INJECTION}, headers=auth["viewer_test"])
    assert response.status_code == 200
    assert response.json()["total"] == 0
    _assert_no_internal_leak(response)


def test_sql_injection_in_license_and_user_search(client, auth, db) -> None:
    facility = create_facility(db)
    create_license(db, facility, "LIC-800")

    licenses = client.get("/licenses", params={"search": INJECTION}, headers=auth["viewer_test"])
    assert licenses.status_code == 200
    assert licenses.json()["total"] == 0
    _assert_no_internal_leak(licenses)

    users = client.get("/users", params={"search": INJECTION}, headers=auth["admin_test"])
    assert users.status_code == 200
    assert users.json()["total"] == 0
    _assert_no_internal_leak(users)


def test_sql_injection_in_login_returns_generic_error(client, users) -> None:
    response = client.post("/auth/login", json={"username": INJECTION, "password": INJECTION})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password."
    _assert_no_internal_leak(response)


def test_wildcards_are_treated_literally(client, auth, db) -> None:
    create_facility(db, "Acme Materials", "REG-801")
    create_facility(db, "A_me Facility", "REG-802")

    percent = client.get("/facilities", params={"search": "%"}, headers=auth["viewer_test"])
    assert percent.status_code == 200
    assert percent.json()["total"] == 0

    underscore = client.get("/facilities", params={"search": "_"}, headers=auth["viewer_test"])
    assert underscore.status_code == 200
    assert underscore.json()["total"] == 1
    assert underscore.json()["items"][0]["registration_number"] == "REG-802"


def test_mass_assignment_is_rejected(client, auth, db) -> None:
    response = client.post(
        "/facilities",
        json={
            "name": "Mass Assignment",
            "registration_number": "REG-803",
            "address": "1 Extra Field Street",
            "is_deleted": True,
            "status": "closed",
        },
        headers=auth["admin_test"],
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "extra_forbidden"

    facility = create_facility(db, "Existing", "REG-804")
    update = client.put(
        f"/facilities/{facility.id}",
        json={"is_deleted": True},
        headers=auth["admin_test"],
    )
    assert update.status_code == 422
    assert client.get(f"/facilities/{facility.id}", headers=auth["admin_test"]).status_code == 200


def test_type_confusion_and_path_injection_are_rejected(client, auth, db) -> None:
    facility = create_facility(db)
    bad_type = client.post(
        "/licenses",
        json={
            "facility_id": facility.id,
            "license_number": "LIC-801",
            "type": "operating",
            "issue_date": "not-a-date",
            "expiry_date": "2027-01-01",
        },
        headers=auth["admin_test"],
    )
    assert bad_type.status_code == 422

    path_injection = client.get("/facilities/1%20OR%201=1", headers=auth["admin_test"])
    assert path_injection.status_code == 422
    _assert_no_internal_leak(path_injection)

    pagination = client.get("/facilities?page=0&size=1000", headers=auth["admin_test"])
    assert pagination.status_code == 422
