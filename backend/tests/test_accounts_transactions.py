from fastapi.testclient import TestClient


def test_health_and_seeded_accounts(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    accounts = client.get("/accounts")
    assert accounts.status_code == 200
    assert [account["code"] for account in accounts.json()] == ["cash", "card"]

    balances = client.get("/accounts/balances")
    assert balances.status_code == 200
    assert balances.json()["cash"]["balance"] == "0.00"
    assert balances.json()["card"]["balance"] == "0.00"


def test_transactions_update_balances_and_filters(client: TestClient) -> None:
    income = client.post(
        "/transactions",
        json={
            "account_code": "cash",
            "counterparty_name": "Cliente Principal",
            "concept_name": "Venta",
            "type": "income",
            "amount": "100.50",
            "transaction_date": "2026-05-10",
        },
    )
    assert income.status_code == 201

    expense = client.post(
        "/transactions",
        json={
            "account_code": "cash",
            "counterparty_name": "Cliente Principal",
            "concept_name": "Retirada",
            "type": "expense",
            "amount": "20.25",
            "transaction_date": "2026-05-10",
        },
    )
    assert expense.status_code == 201

    balances = client.get("/accounts/balances").json()
    assert balances["cash"]["balance"] == "80.25"

    filtered = client.get("/transactions", params={"type": "income", "counterparty": "principal"})
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["concept"]["name"] == "Venta"

    update = client.put(f"/transactions/{expense.json()['id']}", json={"amount": "30.50"})
    assert update.status_code == 200
    assert client.get("/accounts/balances").json()["cash"]["balance"] == "70.00"

    delete = client.delete(f"/transactions/{income.json()['id']}")
    assert delete.status_code == 204
    assert client.get("/accounts/balances").json()["cash"]["balance"] == "-30.50"


def test_transaction_validation_errors(client: TestClient) -> None:
    missing_account = client.post(
        "/transactions",
        json={
            "counterparty_name": "Cliente",
            "concept_name": "Venta",
            "type": "income",
            "amount": "10.00",
            "transaction_date": "2026-05-10",
        },
    )
    assert missing_account.status_code == 422

    invalid_amount = client.post(
        "/transactions",
        json={
            "account_code": "cash",
            "counterparty_name": "Cliente",
            "concept_name": "Venta",
            "type": "income",
            "amount": "0",
            "transaction_date": "2026-05-10",
        },
    )
    assert invalid_amount.status_code == 422
