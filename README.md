# Libro de Caja

Aplicacion web para gestionar un libro de caja basico con cuentas de efectivo y tarjeta.

## Fase actual

La fase 1 deja preparada la base del proyecto:

- MySQL en Docker.
- Backend Python con FastAPI.
- Frontend React con Vite.
- Docker Compose para levantar todos los servicios.
- Endpoint de salud en `/health`.

La fase 2 anade:

- SQLAlchemy configurado.
- Alembic configurado.
- Modelos `Account`, `Counterparty`, `Concept` y `Transaction`.
- Migracion inicial de base de datos.
- Cuentas iniciales `cash` y `card`.

La fase 3 anade:

- `GET /accounts`
- `GET /accounts/balances`
- CRUD de movimientos en `/transactions`
- Filtros por fecha, cuenta, tipo, nombre/empresa y concepto.
- Creacion automatica de nombre/empresa y concepto al crear un movimiento.
- Recalculo de saldos tras crear, editar o eliminar movimientos.

La fase 4 anade:

- CRUD de nombres/empresas en `/counterparties`.
- CRUD de conceptos en `/concepts`.
- Busqueda con `?q=texto` para autocompletado.
- Proteccion para no borrar nombres/empresas o conceptos con movimientos asociados.
- Los nombres/empresas guardan DNI/CIF, direccion, telefono y email.

La fase 5 anade:

- Interfaz principal en castellano.
- Menu lateral izquierdo.
- Paleta blanca y azul claro.
- Opcion de modo oscuro.
- Dashboard de saldos.
- Tabla de movimientos con filtros.
- Formulario de entradas y retiradas conectado con la API.
- Gestion visual de nombres/empresas y conceptos.

La fase 6 anade:

- Boton de impresion del libro de caja filtrado.
- Estilos de impresion limpios, sin menu ni controles.
- Exportacion PDF desde `GET /reports/cashbook/pdf`.
- El PDF respeta filtros de fecha, cuenta, tipo, nombre/empresa y concepto.

La fase 7 anade:

- Envio del informe por email desde `POST /reports/cashbook/email`.
- Adjunta el PDF del libro de caja con los filtros actuales.
- Configuracion SMTP optimizada para Microsoft 365 / Office 365.
- Dialogo en frontend para destinatario, asunto y mensaje.
- Mensajes claros si SMTP no esta configurado o Office 365 rechaza la autenticacion.

La fase 8 anade:

- Pruebas automaticas del backend con `pytest`.
- Cobertura de cuentas, saldos, movimientos, tablas maestras, PDF y email.
- Validacion de build del frontend.
- Documentacion de instalacion, configuracion y comprobaciones.

## Arranque

```bash
docker compose up --build
```

Al arrancar el contenedor del backend se ejecuta automaticamente:

```bash
alembic upgrade head
```

Servicios:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Health check: http://localhost:8000/health
- Documentacion API: http://localhost:8000/docs
- MySQL: localhost:3306

## Comandos de validacion

Con Docker arrancado:

```bash
docker compose exec -T backend pytest
docker compose exec -T frontend npm run build
```

Comprobaciones manuales recomendadas:

- Abrir http://localhost:5173.
- Crear una entrada en efectivo.
- Crear una retirada en tarjeta.
- Confirmar que los saldos cambian.
- Filtrar el libro de caja.
- Exportar PDF.
- Abrir el dialogo de envio por email.

## Ejemplo de movimiento

```bash
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "account_code": "cash",
    "counterparty_name": "Cliente ejemplo",
    "concept_name": "Venta",
    "type": "income",
    "amount": "100.50",
    "transaction_date": "2026-05-10"
  }'
```

## Busquedas para autocompletado

```bash
curl "http://localhost:8000/counterparties?q=cliente"
curl "http://localhost:8000/concepts?q=venta"
```

## Ejemplo de nombre o empresa

```bash
curl -X POST http://localhost:8000/counterparties \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Empresa ejemplo",
    "dni_cif": "B12345678",
    "address": "Calle Mayor 1",
    "phone": "600111222",
    "email": "empresa@example.com"
  }'
```

## Exportar PDF

```bash
curl -o libro-de-caja.pdf "http://localhost:8000/reports/cashbook/pdf?account_code=cash"
```

## Enviar informe por email

```bash
curl -X POST http://localhost:8000/reports/cashbook/email \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": "destino@empresa.com",
    "subject": "Libro de caja",
    "message": "Adjunto el informe solicitado.",
    "filters": {
      "account_code": "cash"
    }
  }'
```

## Configuracion

Copia `.env.example` a `.env` si quieres personalizar puertos, credenciales o configuracion SMTP.

Para Microsoft 365 / Office 365 usa:

```text
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_STARTTLS=true
SMTP_USER=correo@tu-dominio.com
SMTP_PASSWORD=tu_password_o_password_de_aplicacion
SMTP_FROM=correo@tu-dominio.com
```

La cuenta usada para enviar debe tener SMTP AUTH habilitado. En Microsoft 365 puede estar deshabilitado por seguridad a nivel de organizacion o de buzon.

## Notas de calidad

- Los importes se guardan como decimal en backend.
- Los saldos se calculan desde movimientos, no se editan manualmente.
- Los nombres/empresas y conceptos se normalizan para evitar duplicados evidentes.
- No se permite borrar nombres/empresas o conceptos con movimientos asociados.
- El backend devuelve errores claros cuando SMTP no esta configurado.
