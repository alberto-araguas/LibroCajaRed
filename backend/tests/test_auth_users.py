from fastapi.testclient import TestClient


def test_login_and_current_user(client: TestClient) -> None:
    login = client.post("/auth/login", json={"username": "admin", "password": "admin123"})

    assert login.status_code == 200
    data = login.json()
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin"
    assert data["user"]["is_admin"] is True

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "admin"


def test_admin_can_create_users(client: TestClient) -> None:
    created = client.post(
        "/users",
        json={
            "username": "operador",
            "password": "secreto123",
            "full_name": "Operador",
            "is_admin": False,
        },
    )

    assert created.status_code == 201
    assert created.json()["username"] == "operador"
    assert created.json()["is_admin"] is False

    users = client.get("/users")
    assert users.status_code == 200
    assert {user["username"] for user in users.json()} == {"admin", "operador"}


def test_duplicate_user_is_rejected(client: TestClient) -> None:
    duplicate = client.post(
        "/users",
        json={"username": "admin", "password": "secreto123"},
    )

    assert duplicate.status_code == 409


def test_admin_can_update_user_and_password(client: TestClient) -> None:
    created = client.post(
        "/users",
        json={
            "username": "editable",
            "password": "secreto123",
            "full_name": "Editable",
        },
    )
    assert created.status_code == 201

    updated = client.put(
        f"/users/{created.json()['id']}",
        json={
            "username": "editable2",
            "password": "nuevo123",
            "full_name": "Usuario Editable",
            "is_admin": True,
            "is_active": True,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["username"] == "editable2"
    assert updated.json()["full_name"] == "Usuario Editable"
    assert updated.json()["is_admin"] is True

    old_login = client.post("/auth/login", json={"username": "editable2", "password": "secreto123"})
    assert old_login.status_code == 401
    new_login = client.post("/auth/login", json={"username": "editable2", "password": "nuevo123"})
    assert new_login.status_code == 200


def test_admin_can_lookup_transaction_creator(client: TestClient) -> None:
    created_user = client.post(
        "/users",
        json={
            "username": "cajero",
            "password": "secreto123",
            "full_name": "Cajero",
        },
    )
    assert created_user.status_code == 201

    login = client.post("/auth/login", json={"username": "cajero", "password": "secreto123"})
    cashier_token = login.json()["access_token"]
    admin_authorization = client.headers["Authorization"]
    client.headers.update({"Authorization": f"Bearer {cashier_token}"})
    transaction = client.post(
        "/transactions",
        json={
            "account_code": "cash",
            "counterparty_name": "Cliente usuario",
            "concept_name": "Venta usuario",
            "type": "income",
            "amount": "20.00",
            "transaction_date": "2026-05-10",
        },
    )
    assert transaction.status_code == 201

    forbidden = client.get(f"/users/movement-lookup/{transaction.json()['id']}")
    assert forbidden.status_code == 403

    client.headers.update({"Authorization": admin_authorization})
    lookup = client.get(f"/users/movement-lookup/{transaction.json()['id']}")

    assert lookup.status_code == 200
    assert lookup.json()["username"] == "cajero"
    assert lookup.json()["full_name"] == "Cajero"
