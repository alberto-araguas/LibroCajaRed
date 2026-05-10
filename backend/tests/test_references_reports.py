from fastapi.testclient import TestClient


def test_counterparty_crud_and_delete_protection(client: TestClient) -> None:
    created = client.post(
        "/counterparties",
        json={
            "name": "Empresa Azul",
            "dni_cif": "B12345678",
            "address": "Calle Mayor 1",
            "phone": "600111222",
            "email": "empresa.azul@example.com",
        },
    )
    assert created.status_code == 201
    assert created.json()["dni_cif"] == "B12345678"
    assert created.json()["address"] == "Calle Mayor 1"
    assert created.json()["phone"] == "600111222"
    assert created.json()["email"] == "empresa.azul@example.com"
    counterparty_id = created.json()["id"]

    duplicate = client.post("/counterparties", json={"name": " empresa   azul "})
    assert duplicate.status_code == 409

    search = client.get("/counterparties", params={"q": "600111222"})
    assert search.status_code == 200
    assert len(search.json()) == 1

    updated = client.put(
        f"/counterparties/{counterparty_id}",
        json={
            "name": "Empresa Azul SL",
            "dni_cif": "B87654321",
            "address": "Avenida Nueva 2",
            "phone": "600333444",
            "email": "azul.sl@example.com",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["normalized_name"] == "empresa azul sl"
    assert updated.json()["dni_cif"] == "B87654321"
    assert updated.json()["email"] == "azul.sl@example.com"

    transaction = client.post(
        "/transactions",
        json={
            "account_code": "cash",
            "counterparty_name": "Empresa Azul SL",
            "concept_name": "Venta protegida",
            "type": "income",
            "amount": "10.00",
            "transaction_date": "2026-05-10",
        },
    )
    assert transaction.status_code == 201

    protected = client.delete(f"/counterparties/{counterparty_id}")
    assert protected.status_code == 409


def test_concept_crud_and_delete_protection(client: TestClient) -> None:
    created = client.post("/concepts", json={"name": "Venta directa"})
    assert created.status_code == 201
    concept_id = created.json()["id"]

    duplicate = client.post("/concepts", json={"name": "venta   directa"})
    assert duplicate.status_code == 409

    search = client.get("/concepts", params={"q": "directa"})
    assert search.status_code == 200
    assert len(search.json()) == 1

    updated = client.put(f"/concepts/{concept_id}", json={"name": "Venta tienda"})
    assert updated.status_code == 200
    assert updated.json()["normalized_name"] == "venta tienda"

    transaction = client.post(
        "/transactions",
        json={
            "account_code": "cash",
            "counterparty_name": "Cliente protegido",
            "concept_name": "Venta tienda",
            "type": "income",
            "amount": "10.00",
            "transaction_date": "2026-05-10",
        },
    )
    assert transaction.status_code == 201

    protected = client.delete(f"/concepts/{concept_id}")
    assert protected.status_code == 409


def test_pdf_report_is_generated(client: TestClient) -> None:
    client.post(
        "/transactions",
        json={
            "account_code": "card",
            "counterparty_name": "Cliente PDF",
            "concept_name": "Venta PDF",
            "type": "income",
            "amount": "55.00",
            "transaction_date": "2026-05-10",
        },
    )

    response = client.get("/reports/cashbook/pdf", params={"account_code": "card"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 1000


def test_email_report_requires_smtp_config(client: TestClient) -> None:
    response = client.post(
        "/reports/cashbook/email",
        json={
            "recipient": "destino@example.com",
            "subject": "Libro de caja",
            "message": "Informe de prueba",
            "filters": {},
        },
    )

    assert response.status_code == 503
    assert "SMTP no está configurado" in response.json()["detail"]
