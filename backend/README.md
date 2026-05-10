# Backend

Backend FastAPI del Libro de Caja.

## Ejecutar pruebas

Desde la raiz del proyecto:

```bash
docker compose exec -T backend pytest
```

Las pruebas usan SQLite en memoria y no modifican la base MySQL de desarrollo.

## Endpoints principales

- `GET /health`
- `GET /accounts`
- `GET /accounts/balances`
- `GET /transactions`
- `POST /transactions`
- `PUT /transactions/{id}`
- `DELETE /transactions/{id}`
- `GET /counterparties`
- `GET /concepts`
- `GET /reports/cashbook/pdf`
- `POST /reports/cashbook/email`
