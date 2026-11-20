"""Integration tests for user administration and profiles."""

from __future__ import annotations

from tests.conftest import TEST_PASSWORD
from tests.factories import create_user

NEW_PASSWORD = "NewUserPassword_123!"
VIEWER_NEW_PASSWORD = "NewViewerPassword_123!"


def test_admin_creates_user_and_duplicate_is_rejected(client, auth) -> None:
    payload = {
        "username": "new_inspector",
        "password": NEW_PASSWORD,
        "full_name": "New Inspector",
        "role": "inspector",
    }
    created = client.post("/users", json=payload, headers=auth["admin_test"])
    assert created.status_code == 201
    body = created.json()
    assert body["username"] == "new_inspector"
    assert body["role"] == "inspector"
    assert body["is_active"] is True
    assert "password" not in body

    duplicate = client.post("/users", json=payload, headers=auth["admin_test"])
    assert duplicate.status_code == 409


def test_user_list_filters_and_paginates(client, auth) -> None:
    response = client.get("/users?role=inspector&size=1&page=1", headers=auth["admin_test"])
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["pages"] == 2
    assert len(body["items"]) == 1

    second = client.get("/users?role=inspector&size=1&page=2", headers=auth["admin_test"])
    assert second.status_code == 200
    assert second.json()["page"] == 2
    assert second.json()["items"][0]["id"] != body["items"][0]["id"]

    search = client.get("/users?search=Viewer", headers=auth["admin_test"])
    assert search.status_code == 200
    assert search.json()["total"] == 1
    assert search.json()["items"][0]["username"] == "viewer_test"

    active = client.get("/users?is_active=false", headers=auth["admin_test"])
    assert active.status_code == 200
    assert active.json()["total"] == 0


def test_read_user_and_missing_user(client, auth, users) -> None:
    response = client.get(f"/users/{users['viewer_test'].id}", headers=auth["admin_test"])
    assert response.status_code == 200
    assert response.json()["role"] == "viewer"
    assert client.get("/users/999999", headers=auth["admin_test"]).status_code == 404


def test_admin_updates_role_name_and_password(client, auth, login, users) -> None:
    viewer_id = users["viewer_test"].id
    response = client.put(
        f"/users/{viewer_id}",
        json={"role": "inspector", "full_name": "Promoted Viewer"},
        headers=auth["admin_test"],
    )
    assert response.status_code == 200
    assert response.json()["role"] == "inspector"
    assert response.json()["full_name"] == "Promoted Viewer"

    me = client.get("/users/me", headers=auth["viewer_test"])
    assert me.status_code == 200
    assert me.json()["role"] == "inspector"

    changed = client.put(
        f"/users/{viewer_id}",
        json={"password": NEW_PASSWORD},
        headers=auth["admin_test"],
    )
    assert changed.status_code == 200
    assert (
        client.post(
            "/auth/login", json={"username": "viewer_test", "password": TEST_PASSWORD}
        ).status_code
        == 401
    )
    assert login("viewer_test", NEW_PASSWORD)


def test_admin_cannot_change_own_role_or_deactivate_self(client, auth) -> None:
    me = client.get("/users/me", headers=auth["admin_test"]).json()
    assert (
        client.put(
            f"/users/{me['id']}",
            json={"role": "viewer"},
            headers=auth["admin_test"],
        ).status_code
        == 409
    )
    assert (
        client.put(
            f"/users/{me['id']}",
            json={"is_active": False},
            headers=auth["admin_test"],
        ).status_code
        == 409
    )
    assert client.delete(f"/users/{me['id']}", headers=auth["admin_test"]).status_code == 409


def test_admin_deactivates_user_and_tokens_stop_working(client, auth, users) -> None:
    viewer_id = users["viewer_test"].id
    deleted = client.delete(f"/users/{viewer_id}", headers=auth["admin_test"])
    assert deleted.status_code == 204
    assert client.get("/users/me", headers=auth["viewer_test"]).status_code == 401

    listed = client.get(f"/users/{viewer_id}", headers=auth["admin_test"]).json()
    assert listed["is_active"] is False

    again = client.delete(f"/users/{viewer_id}", headers=auth["admin_test"])
    assert again.status_code == 204
    assert (
        client.post(
            "/auth/login", json={"username": "viewer_test", "password": TEST_PASSWORD}
        ).status_code
        == 401
    )


def test_profile_update_and_mass_assignment_rejection(client, auth) -> None:
    updated = client.put(
        "/users/me",
        json={"full_name": "Viewer Renamed"},
        headers=auth["viewer_test"],
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Viewer Renamed"

    attempt = client.put("/users/me", json={"role": "admin"}, headers=auth["viewer_test"])
    assert attempt.status_code == 422
    assert client.get("/users/me", headers=auth["viewer_test"]).json()["role"] == "viewer"

    assert client.put("/users/me", json={}, headers=auth["viewer_test"]).status_code == 422


def test_profile_password_change_requires_current_password(client, auth, login) -> None:
    wrong = client.put(
        "/users/me",
        json={
            "current_password": "NotThePassword_123!",
            "new_password": VIEWER_NEW_PASSWORD,
        },
        headers=auth["viewer_test"],
    )
    assert wrong.status_code == 400

    missing = client.put(
        "/users/me",
        json={"new_password": VIEWER_NEW_PASSWORD},
        headers=auth["viewer_test"],
    )
    assert missing.status_code == 422

    changed = client.put(
        "/users/me",
        json={
            "current_password": TEST_PASSWORD,
            "new_password": VIEWER_NEW_PASSWORD,
        },
        headers=auth["viewer_test"],
    )
    assert changed.status_code == 200
    assert login("viewer_test", VIEWER_NEW_PASSWORD)


def test_admin_user_update_validation(client, auth, db, password_hash) -> None:
    target = create_user(db, "temp_user", "viewer", password_hash)
    empty = client.put(f"/users/{target.id}", json={}, headers=auth["admin_test"])
    assert empty.status_code == 422
    missing = client.put("/users/999999", json={"full_name": "X Y"}, headers=auth["admin_test"])
    assert missing.status_code == 404
